# Riscos e limitações

## Como usar este registro

Risco é uma incerteza que pode afetar o produto; limitação é uma capacidade conscientemente ausente ou reduzida. Este documento deve ser revisto ao final de cada etapa, antes de produção e sempre que houver nova integração, tipo de dado ou nível de autonomia.

Escala usada: probabilidade e impacto `Baixo`, `Médio` ou `Alto`. Um risco alto sem mitigação ou aceite explícito bloqueia a entrega afetada.

## Registro inicial de riscos

| ID | Risco | Prob. | Impacto | Mitigação principal | Sinal de alerta |
|---|---|---:|---:|---|---|
| R-01 | Vazamento entre organizações por filtro ausente. | Média | Alto | Contexto obrigatório de tenant, repositórios escopados, constraints e testes negativos. | Consulta sem `organization_id` ou teste cruzado falhando. |
| R-02 | Papel ou sessão permitir ação indevida. | Média | Alto | Autorização no backend por ação, menor privilégio, biblioteca mantida e audit log. | Ação funciona por API, mas deveria estar apenas oculta na UI. |
| R-03 | Segredo entrar no Git, imagem ou log. | Média | Alto | `.env.example` sem valor real, scanner, mascaramento, secret manager e rotação. | Padrão de chave detectado ou erro imprime configuração. |
| R-04 | IA inventar fatos, serviços, preços ou métricas. | Alta | Alto | Mock identificável, grounding no Brand Kit, validação e revisão humana. | Resultado sem fonte ou com campo ausente preenchido como fato. |
| R-05 | Conteúdo veterinário causar dano ou promessa irregular. | Média | Alto | Classificação de sensibilidade, revisão profissional e proibição de orientação automática. | Menção a diagnóstico, prescrição, cura ou garantia. |
| R-06 | Escopo da visão final atrasar o fluxo vertical. | Alta | Alto | Milestones, critérios do primeiro ciclo e bloqueio das integrações futuras. | Trabalho em Ads/WhatsApp antes do fluxo de aprovação funcionar. |
| R-07 | Acoplamento a um provider elevar custo ou impedir operação. | Média | Alto | Portas/adaptadores, mock obrigatório, Hermes opcional e testes de contrato. | Regra de domínio importa SDK de fornecedor. |
| R-08 | Fallback enviar dados a terceiro não autorizado. | Baixa | Alto | Allowlist por organização/finalidade e fallback explícito. | Provider muda sem registro ou aviso. |
| R-09 | Aprovação ocorrer sobre versão errada ou alterada. | Média | Alto | Versão imutável, hash/snapshot, transação e controle de concorrência. | Conteúdo muda após entrar em `CLIENT_REVIEW`. |
| R-10 | Retry duplicar e-mail, aprovação ou futura escrita externa. | Média | Alto | Idempotência, outbox/jobs e testes de reprocessamento. | Mesmo evento produz múltiplas decisões ou avisos. |
| R-11 | Notificações em excesso reduzirem confiança. | Média | Médio | Preferências, agrupamento, prioridade e métricas de entrega. | Usuários ignoram pendências ou pedem desativação total. |
| R-12 | Worker acumular jobs silenciosamente. | Média | Alto | Heartbeat, idade da fila, tentativas limitadas, alerta e runbook. | Job mais antigo cresce e não há consumo. |
| R-13 | Upload malicioso ou arquivo privado ficar público. | Média | Alto | Validação real, URL assinada, sanitização e varredura em produção. | URL permanente sem autenticação ou MIME divergente. |
| R-14 | Tratamento LGPD não ter finalidade/retenção definida. | Média | Alto | Inventário, contrato de papéis, minimização, processos de titular e retenção. | Dado sem responsável, base ou prazo. |
| R-15 | Audit log vazar dado sensível ou poder ser alterado. | Baixa | Alto | Eventos mínimos, mascaramento, acesso restrito e append-only lógico. | Token/prompt pessoal em evento ou update por usuário comum. |
| R-16 | Ambiente demo ser confundido com operação real. | Média | Médio | Identificação visual de mock, dados fictícios e integrações desabilitadas. | Usuário interpreta conteúdo/métrica mock como publicado. |
| R-17 | UX móvel tornar aprovação difícil ou ambígua. | Média | Alto | Mobile first, poucos botões, teste com viewport real e acessibilidade. | Rolagem lateral, alvo pequeno ou versão não visível. |
| R-18 | Migrations causarem indisponibilidade ou perda. | Baixa | Alto | Expandir/migrar/contrair, homologação, backup e rollback ensaiado. | DDL destrutivo sem plano ou execução concorrente. |
| R-19 | Dependência vulnerável comprometer a aplicação. | Média | Alto | Lockfiles, atualização, auditoria e correção antes da entrega. | Vulnerabilidade crítica explorável sem aceite formal. |
| R-20 | Custo e latência de IA crescerem sem visibilidade. | Média | Médio | Limites por tarefa, timeout, modelos locais, registro de custo confirmado. | Chamadas sem orçamento, duração ou provider identificado. |
| R-21 | Fluxo provisório de revisor revelar disponibilidade de e-mail ou conceder acesso sem convite verificável. | Média | Alto | Endpoint bloqueado fora de desenvolvimento/teste, mensagem genérica e substituição por convite de uso único antes de dados reais. | Endpoint provisório exposto em ambiente compartilhado. |
| R-22 | Rate limit local divergir entre réplicas ou enxergar apenas o proxy do frontend. | Média | Alto | Limites por identidade/origem, armazenamento local limitado e store compartilhado com proxies confiáveis antes de escalar. | Bloqueio coletivo ou tentativas distribuídas sem contenção. |
| R-23 | Escrita interna incoerente cruzar organização e empresa apesar dos filtros HTTP. | Baixa | Alto | Serviços escopados, testes negativos e evolução das FKs compostas/constraints antes de novos escritores internos. | Job, script ou integração grava IDs de tenants diferentes. |
| R-24 | Ambiente compartilhado usar perfil ou storage local por erro de configuração. | Baixa | Alto | Valores de ambiente tipados, guardas fail-closed e credenciais/TLS gerenciados no gate M7. | Alias como `prod`, endpoint HTTP ou credencial MinIO local fora do desenvolvimento. |

## Riscos de autonomia

### Permitido na versão 1.0

- geração de rascunhos com provider mock ou provider autorizado;
- classificação e organização de tarefas;
- criação de notificação interna após evento válido;
- leitura de dados internos conforme papel;
- registro técnico e de auditoria.

### Exige ação humana explícita

- enviar conteúdo ao cliente;
- aprovar, pedir alteração ou rejeitar;
- registrar publicação manual;
- ativar provider real e definir sua finalidade;
- convidar usuário ou alterar papel.

### Bloqueado na versão 1.0

- publicar automaticamente em rede social;
- responder mensagem em nome do cliente;
- criar, editar, pausar ou financiar campanha real;
- alterar orçamento ou gerar gasto;
- enviar campanha em massa;
- fornecer orientação médica ou veterinária;
- usar dados de uma organização para treinar ou sugerir conteúdo de outra;
- considerar silêncio como aprovação.

Qualquer mudança de nível exige ADR, revisão de segurança/LGPD, critérios de reversão, limites, alertas e aprovação do proprietário.

## Limitações conhecidas da versão 1.0

- O provider mock demonstra o fluxo, não a qualidade final de um modelo comercial.
- Hermes é opcional; sua indisponibilidade reduz capacidades locais, mas não impede o núcleo.
- Publicação é registrada manualmente e não confirma o estado real de uma rede social.
- Relatórios usam dados registrados no sistema e não métricas sincronizadas de plataformas.
- E-mail pode operar em caixa local/mock até haver configuração transacional aprovada.
- Geração automática de vídeo não existe; há roteiro, storyboard, prompts e upload.
- Centro de Integrações pode mostrar capacidades futuras desabilitadas.
- A fila baseada em PostgreSQL atende a escala inicial; Redis/fila dedicada pode ser necessário com aumento de volume.
- A aplicação é web mobile first, não aplicativo móvel nativo.
- O sistema não é prontuário e não deve receber dados clínicos sensíveis.
- White label, cobrança, marketplace e API pública não fazem parte desta versão.
- A criação direta de revisor e senha por um administrador é apenas um auxílio local; convite com aceite, uso único e resposta anti-enumeração é obrigatório antes de uso com pessoas reais.
- O rate limiter em memória é limitado e adequado a uma única instância local; múltiplas réplicas exigem store compartilhado e configuração de proxy confiável.
- A elevação excepcional de `SUPER_ADMIN`, com justificativa operacional própria, continua pendente; as rotas atuais ainda o mantêm dentro da membership e organização selecionadas.
- As rotas validam tenant e empresa, mas constraints compostas de todas as relações serão ampliadas antes de permitir novos processos de escrita direta no banco.
- O perfil atual endurece o valor exato `production`; aliases, storage remoto com TLS e credenciais gerenciadas serão fechados de forma fail-closed no gate M7 antes de qualquer ambiente compartilhado.

## Dependências e hipóteses

- O proprietário fornecerá conteúdo de marca e responsáveis reais para o piloto.
- Um profissional habilitado estará disponível para revisar conteúdo veterinário sensível.
- Domínio, e-mail transacional e infraestrutura de produção serão definidos antes do go-live.
- Bases legais, contratos e prazos de retenção receberão validação adequada antes de dados reais.
- Providers reais terão termos, custos, localização de dados e limites avaliados antes da ativação.
- A equipe manterá pequenas entregas, migrations, testes e documentação atualizados.

Se uma hipótese não se confirmar, ela deve virar risco ou bloqueio explícito; o sistema não deve inventar uma solução comercial, jurídica ou clínica.

## Fora do escopo confirmado

- repositório/site institucional `DevMark-ia`;
- Instagram e Facebook com publicação direta;
- Meta Ads e Google Ads reais;
- gasto ou aumento automático de orçamento;
- WhatsApp Business oficial;
- geração automática de vídeo;
- cobrança automática, white label e marketplace;
- autonomia total;
- aconselhamento veterinário automático;
- garantias de desempenho comercial ou métricas não observadas.

## Critérios de aceite deste registro

1. **RISK-01:** cada risco alto possui mitigação, responsável funcional e sinal observável antes da produção.
2. **RISK-02:** nenhuma funcionalidade bloqueada está acessível por API, worker ou botão ativo.
3. **RISK-03:** modo mock é claramente distinguível de integração e dado reais.
4. **RISK-04:** falhas conhecidas aparecem no changelog/backlog ou aceite formal, não são ocultadas.
5. **RISK-05:** riscos de isolamento, conteúdo veterinário, segredos e aprovação possuem testes correspondentes.
6. **RISK-06:** a revisão de go-live confirma contratos/LGPD, backups, responsável clínico e infraestrutura.
7. **RISK-07:** nova integração ou autonomia atualiza este documento e gera ADR quando muda uma decisão estrutural.
8. **RISK-08:** o registro é revisado ao fim de cada milestone e após incidente relevante.
