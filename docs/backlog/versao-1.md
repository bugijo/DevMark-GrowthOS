# Backlog da versão 1.0 — Clínica Piloto

## Objetivo

Entregar uma aplicação utilizável por uma clínica veterinária que prove o ciclo completo de criação e aprovação de conteúdo, com dados isolados por organização, providers mock, auditoria e execução por Docker Compose.

Este backlog cobre a versão 1.0 descrita no prompt mestre. A ordem prática de entrega está em [`docs/milestones/versao-1.md`](../milestones/versao-1.md).

## Regras do backlog

Prioridades:

- **P0:** bloqueia o primeiro fluxo vertical ou a segurança básica;
- **P1:** obrigatória para declarar a versão 1.0 pronta;
- **P2:** melhoria que só entra depois dos itens obrigatórios, sem atrasar a versão.

Estados sugeridos: `BACKLOG`, `READY`, `IN_PROGRESS`, `IN_REVIEW`, `DONE` e `BLOCKED`.

Um item só pode entrar em `DONE` quando:

- seus critérios de aceite podem ser demonstrados e estão cobertos por testes proporcionais ao risco;
- autorização, organização e audit log foram avaliados no backend;
- API, banco e interface estão integrados quando o item possui tela;
- lint, tipos e testes afetados passam sem rede externa ou API paga;
- documentação, OpenAPI, migração e changelog foram atualizados quando aplicável;
- não contém segredo, dado real de cliente ou atalho que permita acesso cruzado.

## Restrições inegociáveis

- O repositório `bugijo/DevMark-ia` não faz parte deste trabalho.
- O provider mock é suficiente para executar e testar toda a versão 1.0.
- Não há publicação social automática, Meta Ads real, Google Ads real, gasto automático ou WhatsApp oficial.
- Conteúdo veterinário ou de saúde exige revisão profissional.
- Dados de um cliente não podem ser usados por outro sem autorização explícita.

## 1. Documentação e decisões

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-DOC-001` | P0 | Documentação-base e ADRs iniciais | — | Os 14 documentos obrigatórios, `README.md`, `AGENTS.md`, `.env.example`, `CONTRIBUTING.md`, `CHANGELOG.md`, backlog, milestones e diretório de ADR existem; outra pessoa identifica escopo, arquitetura, dados, fluxos, riscos e modo de execução. |
| `V1-DOC-002` | P1 | Matriz rastreável de requisitos | `V1-DOC-001` | Cada critério final CAV1-01 a CAV1-25 aponta para implementação e teste; lacunas permanecem visíveis e não são marcadas como concluídas. |

## 2. Fundação do monorepo

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-FND-001` | P0 | Estrutura do monorepo | `V1-DOC-001` | `frontend`, `backend`, `worker`, `shared`, `infra`, `scripts`, `tests` e `.github` têm responsabilidade documentada; builds não dependem de caminhos fora deste repositório. |
| `V1-FND-002` | P0 | Docker Compose local | `V1-FND-001` | Um ambiente limpo sobe frontend, API, worker, PostgreSQL e MinIO com `docker compose up --build`; serviços têm healthcheck e dados persistem após `docker compose down`. |
| `V1-FND-003` | P0 | Configuração, erros e logs estruturados | `V1-FND-001` | Aplicação valida configuração ao iniciar, recusa configuração insegura de produção, devolve erros consistentes com correlation ID e não registra segredos ou dados pessoais desnecessários. |
| `V1-FND-004` | P0 | Lint, tipos, testes e CI | `V1-FND-001` | Backend e frontend oferecem comandos reproduzíveis de lint, tipos e testes; CI executa-os com provider mock, banco de teste e sem credenciais externas. |
| `V1-FND-005` | P1 | Contratos OpenAPI e cliente tipado | `V1-FND-003` | API expõe OpenAPI versionada; respostas de erro e paginação são consistentes; frontend detecta quebra de contrato na CI. |

## 3. Persistência, jobs e dados de demonstração

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-DAT-001` | P0 | PostgreSQL e migrações Alembic | `V1-FND-002` | Banco vazio migra até a revisão mais recente; schema não nasce por `create_all` em operação; teste aplica migrações desde zero. |
| `V1-DAT-002` | P0 | Núcleo multiempresa | `V1-DAT-001` | `users`, `organizations`, `memberships` e `businesses` usam UUID, timestamps, chaves estrangeiras, unicidade e índices coerentes; entidades tenant-aware têm vínculo verificável à organização. |
| `V1-DAT-003` | P0 | Jobs, notificações e audit log persistentes | `V1-DAT-001`, `V1-DAT-002` | Jobs guardam organização, status, tentativas, timeout e erro seguro; notificações e logs são imutáveis pelo fluxo comum e consultáveis somente no tenant autorizado. |
| `V1-DAT-004` | P0 | Seed idempotente de demonstração | `V1-DAT-002` | Seed local cria dados totalmente fictícios para agência e clínica piloto, pode rodar duas vezes sem duplicar registros e é bloqueado em produção. |
| `V1-DAT-005` | P1 | Schema completo da versão 1.0 | `V1-DAT-002` | Migrações cobrem as entidades documentadas usadas na versão 1.0, com organização, integridade referencial, índices e estratégia de exclusão definidas; schema e documentação permanecem alinhados. |

## 4. Autenticação, organizações e papéis

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-AUT-001` | P0 | Login, sessão e logout | `V1-DAT-002`, `V1-FND-003` | Usuário ativo entra com e-mail e senha usando biblioteca mantida; credencial inválida não revela se a conta existe; sessão expira e logout a invalida com segurança. |
| `V1-AUT-002` | P1 | Recuperação de senha | `V1-AUT-001`, `V1-NTF-002` | Solicitação gera token de uso único, curto e armazenado com segurança; mensagem não revela existência da conta; troca invalida token e sessões conforme política. |
| `V1-AUT-003` | P0 | Organizações, memberships e convites | `V1-AUT-001`, `V1-DAT-002` | Admin cria organização, convida usuário e acompanha convite; aceite vincula a membership correta; criação, aceite, revogação e mudança de papel são auditados. |
| `V1-AUT-004` | P0 | RBAC no backend | `V1-AUT-003` | Os oito papéis iniciais possuem capacidades documentadas e aplicadas em casos de uso; requisição direta sem capacidade retorna 403 e não altera dados. |
| `V1-AUT-005` | P0 | Prova de isolamento multiempresa | `V1-AUT-004`, `V1-FND-004` | Testes com duas organizações cobrem listagem, leitura por ID, escrita, aprovação, arquivo, job, notificação e audit log; tentativa cruzada não vaza existência nem dados. |

## 5. Cliente, marca e onboarding

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-CLI-001` | P0 | Cadastro e gestão de cliente | `V1-AUT-004`, `V1-DAT-002` | `AGENCY_ADMIN` cria, lista, consulta e edita um cliente da própria organização; campos são validados; duplicidade e acesso cruzado são tratados; ações relevantes são auditadas. |
| `V1-CLI-002` | P1 | Responsáveis e acesso do cliente | `V1-CLI-001`, `V1-AUT-003` | Agência vincula `CLIENT_OWNER` e `CLIENT_REVIEWER` ao cliente; cada usuário vê apenas a própria empresa e as permissões entram em vigor sem depender do frontend. |
| `V1-BRD-001` | P0 | Brand Kit básico | `V1-CLI-001`, `V1-DAT-005` | Agência salva nome público, descrição, segmento, público, cores, fontes, tom, palavras preferidas/proibidas, slogan, diferenciais, contatos, CTA e restrições; cliente autorizado pode visualizar. |
| `V1-BRD-002` | P1 | Serviços, públicos e objetivos | `V1-BRD-001` | Usuário autorizado mantém serviços, segmentos de público e objetivos por cliente; itens arquivados não somem do histórico e nunca aparecem em outro tenant. |
| `V1-BRD-003` | P1 | Presets visuais | `V1-BRD-001` | Agência cria e edita preset com formato, proporção, paleta, fontes, logo, margens, estilo, regras de texto, prompt-base/negativo, elementos e CTA; preview informa campos ausentes. |
| `V1-BRD-004` | P1 | Upload seguro de logos e referências | `V1-BRD-001`, `V1-FND-002` | Upload aceita apenas tipos/tamanhos permitidos, usa nome gerado, grava metadados e organização, entrega URL assinada e rejeita leitura cruzada. |
| `V1-BRD-005` | P1 | Checklist de onboarding | `V1-BRD-002`, `V1-BRD-003`, `V1-BRD-004`, `V1-CLI-002` | Agência vê progresso e próximo passo para marca, serviços, público, referências, preset, tom, regras, aprovadores e notificações; estado é calculado de dados reais. |

## 6. Providers e orquestração

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-PRV-001` | P0 | Contratos de texto, imagem e e-mail | `V1-FND-003` | Casos de uso dependem de interfaces tipadas com timeout, resultado, erro e metadados seguros; nenhum SDK externo aparece no domínio. |
| `V1-PRV-002` | P0 | Providers mock determinísticos | `V1-PRV-001` | Texto, imagem/template e e-mail funcionam sem rede nem chave; seed igual produz resposta estável; modos de sucesso, atraso e falha podem ser testados. |
| `V1-PRV-003` | P1 | Configuração segura de providers | `V1-PRV-001`, `V1-AUT-004`, `V1-DAT-005` | Admin configura provider por organização sem recuperar segredo em claro; teste de conexão não expõe credencial; conexão, alteração e falha são auditadas. |
| `V1-PRV-004` | P1 | Adaptador Hermes opcional | `V1-PRV-001`, `V1-DAT-003` | Com Hermes desligado ou indisponível, mock mantém o sistema funcional; adaptador respeita timeout, erro normalizado, organização e fallback explícito. |
| `V1-PRV-005` | P1 | Growth Agent mínimo | `V1-PRV-002`, `V1-DAT-003` | Orquestrador escolhe provider permitido pela configuração, cria job rastreável, registra custo estimado quando disponível e explica o resultado sem prometer autonomia externa. |

## 7. Estratégia, calendário e conteúdo

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-CNT-001` | P1 | Estratégia gerada e revisável | `V1-BRD-002`, `V1-PRV-005` | Provider mock gera objetivo, público, posicionamento, pilares, funil e indicadores a partir da marca; usuário interno edita e aprova direção; entradas e versão ficam rastreáveis. |
| `V1-CNT-002` | P1 | Plano e calendário editorial | `V1-CNT-001` | Agência gera e edita calendário com data, canal, formato, objetivo e status; filtros respeitam organização/cliente; cliente vê somente calendário autorizado. |
| `V1-CNT-003` | P0 | Criação de conteúdo mock | `V1-BRD-001`, `V1-PRV-002`, `V1-DAT-005` | Usuário cria conteúdo com legenda, canal, formato, data sugerida, objetivo, público, CTA, observações e prompt visual; resposta mock é persistida como `DRAFT` e auditada. |
| `V1-CNT-004` | P0 | Editor e histórico de versões | `V1-CNT-003` | Edição cria versão imutável numerada e preserva autor/data; é possível comparar versão atual e anterior; aprovação sempre referencia uma versão exata. |
| `V1-CNT-005` | P1 | Ideias, legendas e roteiros | `V1-CNT-001`, `V1-PRV-005` | Mock gera ideias, legendas, roteiro, storyboard, cenas, texto na tela e instruções; usuário escolhe e edita resultados sem perder origem e versão. |
| `V1-CNT-006` | P1 | Template, upload e modo híbrido | `V1-BRD-003`, `V1-BRD-004`, `V1-PRV-002`, `V1-CNT-004` | Conteúdo aceita imagem manual, template e base mock para modo híbrido; texto/logo/CTA são aplicados de forma determinística; validação aponta proporção, margem e campos obrigatórios. |
| `V1-CNT-007` | P1 | Variações de conteúdo | `V1-CNT-005`, `V1-CNT-006` | Usuário solicita uma ou três variações de título, CTA ou visual e adapta feed/story/vertical; cada seleção gera versão identificável, sem sobrescrever a anterior. |

## 8. Aprovação, comentários e auditoria

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-APR-001` | P0 | Máquina de estados e revisão interna | `V1-CNT-004`, `V1-AUT-004`, `V1-DAT-003` | Somente transições oficiais são aceitas; editor envia `DRAFT` para `INTERNAL_REVIEW`; papel autorizado devolve ou envia a versão atual para `CLIENT_REVIEW`; cada transição é atômica e auditada. |
| `V1-APR-002` | P0 | Decisão do cliente | `V1-APR-001`, `V1-CLI-002` | Revisor autorizado aprova, reprova, pede alteração ou salva para depois somente na própria empresa; decisão registra usuário, data, versão e comentário aplicável. |
| `V1-APR-003` | P0 | Comentários e pedido de alteração | `V1-APR-002`, `V1-CNT-004` | Comentários têm autor, organização, visibilidade e data; pedido muda para `CHANGES_REQUESTED`; correção cria nova versão e pode voltar ao fluxo até `APPROVED`. |
| `V1-APR-004` | P0 | Audit log de ponta a ponta | `V1-DAT-003`, `V1-AUT-003` | Login relevante, cliente, marca, conteúdo, versão, transição, decisão, notificação, permissão e publicação manual geram evento com ator, organização, ação, recurso, data e metadados sem segredo; usuário não edita eventos. |
| `V1-APR-005` | P1 | Histórico completo da aprovação | `V1-APR-003`, `V1-APR-004` | Agência e cliente autorizados visualizam linha do tempo com versões, comentários e decisões; visualização não mistura eventos internos proibidos nem dados de outro tenant. |

## 9. Notificações

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-NTF-001` | P0 | Notificações internas e contador | `V1-APR-001`, `V1-DAT-003` | Envio para cliente cria notificação e incrementa pendências do destinatário; leitura é individual, contador é consistente e acesso cruzado é negado; decisão notifica a equipe interna. |
| `V1-NTF-002` | P1 | E-mail por provider | `V1-NTF-001`, `V1-PRV-002` | Evento elegível cria job de e-mail idempotente; console/mock registra entrega sem envio real; falha aplica retries limitados e permanece visível ao operador. |
| `V1-NTF-003` | P1 | Preferências, urgência e resumos | `V1-NTF-002` | Usuário escolhe imediato, diário, semanal ou apenas importante; urgentes seguem regra explícita; lembrete configurável não duplica envio e respeita fuso horário. |

## 10. Interfaces da agência e do cliente

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-UI-001` | P0 | Shell autenticado e navegação por papel | `V1-AUT-001`, `V1-AUT-004` | Login redireciona ao espaço autorizado; menu mostra apenas capacidades aplicáveis; expiração de sessão e falhas são tratadas; navegação por teclado e foco visível funcionam. |
| `V1-UI-002` | P0 | Clientes e Brand Kit integrados | `V1-CLI-001`, `V1-BRD-001`, `V1-UI-001` | Agência cadastra cliente e Brand Kit pela interface, com validação, estados vazios, feedback e dados persistidos na API. |
| `V1-UI-003` | P0 | Editor e envio para aprovação | `V1-CNT-004`, `V1-APR-001`, `V1-UI-001` | Agência cria conteúdo mock, visualiza preview/legenda/metadados, edita e envia para revisão; progresso e erros não deixam estado ambíguo. |
| `V1-UI-004` | P0 | Portal móvel de aprovação | `V1-APR-002`, `V1-NTF-001`, `V1-UI-001` | Cliente vê pendências e abre preview, legenda, canal, formato, data, objetivo, público, CTA, observações e histórico; aprova ou pede alteração em viewport de 360 px sem zoom horizontal. |
| `V1-UI-005` | P1 | Dashboards e estados vazios | `V1-NTF-001`, `V1-CNT-002` | Agência e cliente veem pendências, próximos conteúdos, semana, notificações e resumo permitido; cada estado vazio explica o próximo passo e dados vêm da API. |
| `V1-UI-006` | P1 | Demais telas obrigatórias v1 | `V1-UI-005`, `V1-BRD-005`, `V1-APR-005`, `V1-RPT-001`, `V1-PRV-003` | Navegação cobre marca, presets, serviços, públicos, estratégias, calendário, conteúdos, mídia, aprovações, comentários, notificações, relatórios, providers, configurações e logs conforme o papel, sem tela falsa. |

## 11. Registro de publicação, relatórios e integrações

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-PUB-001` | P1 | Registro manual de publicação | `V1-APR-002`, `V1-APR-004` | Conteúdo `APPROVED` pode ser marcado manualmente como publicado com canal, data, URL opcional e responsável; não chama rede social; ação é idempotente e auditada. |
| `V1-RPT-001` | P1 | Relatório básico | `V1-CNT-002`, `V1-PUB-001` | Período mostra contagens reais por status, aprovações, alterações e publicações manuais; ausência de métrica é indicada, nunca inventada; filtro e exportação simples respeitam tenant. |
| `V1-INT-001` | P1 | Centro de Integrações em modo seguro | `V1-PRV-003`, `V1-AUT-004` | Painel exibe providers disponíveis, modo mock, status, organização, última verificação e erro seguro; nenhum botão faz OAuth/publicação/anúncio real e limites da v1 ficam claros. |

## 12. Segurança, LGPD e operação

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-SEC-001` | P0 | Baseline de segurança da aplicação | `V1-AUT-005`, `V1-FND-003`, `V1-BRD-004` | Login tem rate limit; headers, CORS, cookies e CSRF são configurados conforme o mecanismo de sessão; entradas/uploads são validados; análise de dependências não possui vulnerabilidade crítica conhecida sem tratamento. |
| `V1-SEC-002` | P1 | Controles LGPD iniciais | `V1-DAT-005`, `V1-APR-004` | Inventário, base/finalidade, retenção e acesso são documentados; admin autorizado consegue solicitar exportação/exclusão conforme política; ação preserva obrigações legais e é auditada. |
| `V1-SEC-003` | P1 | Proteção de conteúdo sensível | `V1-CNT-004`, `V1-APR-001` | Conteúdo veterinário/saúde é marcado como revisão profissional obrigatória; sistema bloqueia aprovação final sem confirmação de revisor habilitado e não aceita dado clínico sensível em fixtures/demo. |
| `V1-OPS-001` | P1 | Saúde, backup e recuperação | `V1-FND-002`, `V1-DAT-005` | Healthchecks distinguem processo e prontidão; procedimento de backup/restore de PostgreSQL e arquivos é documentado e testado em ambiente local; falha do worker não corrompe job. |
| `V1-OPS-002` | P1 | Instalação reproduzível | `V1-OPS-001`, `V1-DAT-004` | Pessoa sem contexto clona, copia `.env.example`, sobe Compose, migra/semeia e acessa o fluxo demo seguindo o README; nenhum passo requer segredo ou API paga. |

## 13. Validação e liberação

| ID | Pri. | Entrega | Dependências | Critérios de aceite |
|---|---:|---|---|---|
| `V1-TST-001` | P0 | Suíte do primeiro fluxo vertical | `V1-UI-004`, `V1-APR-004` | Teste ponta a ponta cobre login, organização, cliente, Brand Kit, conteúdo mock, revisão interna, envio, notificação, aprovação e audit log; roda repetidamente em ambiente isolado. |
| `V1-TST-002` | P1 | Matriz de testes da versão 1.0 | `V1-UI-006`, `V1-SEC-003`, `V1-RPT-001` | Unitários, integração, contrato e E2E cobrem caminhos críticos e falhas; CAV1-01 a CAV1-25 têm evidência automatizada ou roteiro justificado. |
| `V1-TST-003` | P1 | Acessibilidade, responsividade e desempenho | `V1-TST-002` | Jornadas críticas passam verificação automatizada de acessibilidade sem erro grave, funcionam em 360/768/1280 px e mantêm limites de resposta documentados com mock local. |
| `V1-REL-001` | P1 | Gate da versão 1.0 | Todos os itens P0 e P1 | CI verde, migração limpa, backup/restore validado, zero segredo detectado, smoke test do Compose passa e os 25 critérios finais têm evidência; riscos residuais e rollback estão registrados. |

## Critérios finais rastreáveis

Estes critérios são obrigatórios e não podem ser substituídos por porcentagem de progresso:

| ID | Evidência de aceite da versão 1.0 |
|---|---|
| `CAV1-01` | Uma agência consegue criar um cliente. |
| `CAV1-02` | O cliente recebe convite. |
| `CAV1-03` | O cliente entra no portal. |
| `CAV1-04` | A agência cadastra Brand Kit. |
| `CAV1-05` | A agência cria um preset visual. |
| `CAV1-06` | O sistema gera uma estratégia. |
| `CAV1-07` | O sistema gera um calendário. |
| `CAV1-08` | O sistema gera um conteúdo. |
| `CAV1-09` | O sistema gera ou recebe uma imagem. |
| `CAV1-10` | O conteúdo passa por revisão interna. |
| `CAV1-11` | O cliente é notificado. |
| `CAV1-12` | O cliente aprova ou pede alteração. |
| `CAV1-13` | A alteração cria nova versão. |
| `CAV1-14` | O cliente aprova a nova versão. |
| `CAV1-15` | O conteúdo aparece no calendário. |
| `CAV1-16` | A publicação pode ser marcada manualmente como publicada. |
| `CAV1-17` | O sistema gera relatório básico com dados reais disponíveis. |
| `CAV1-18` | O audit log registra todas as etapas relevantes. |
| `CAV1-19` | Um cliente não consegue acessar dados de outro. |
| `CAV1-20` | O sistema funciona no celular. |
| `CAV1-21` | Os testes passam. |
| `CAV1-22` | O projeto sobe por Docker Compose. |
| `CAV1-23` | A documentação permite instalação por outra pessoa. |
| `CAV1-24` | Nenhuma chave secreta está no repositório. |
| `CAV1-25` | O sistema funciona com provider mock, sem API paga. |

## Itens explicitamente futuros

Não transformar estes itens em “atalhos” dentro da versão 1.0:

- OAuth e publicação em Instagram/Facebook;
- leitura automática de métricas sociais;
- Google Business Profile e YouTube;
- WhatsApp Business, Telegram e CRM;
- Meta Ads, Google Ads e qualquer alteração financeira;
- vídeo gerado automaticamente;
- automações autônomas, cobrança, white label e marketplace.

Os contratos podem preparar esses caminhos, mas qualquer ação externa permanece desligada e coberta por mock.
