# Histórico de mudanças

Todas as mudanças relevantes do DevMark GrowthOS serão registradas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/). Enquanto a versão 1.0 não for publicada, mudanças entram em **Não lançado**.

## [Não lançado]

### Adicionado

- documentação inicial de visão, escopo, arquitetura, dados, fluxos, providers, segurança, testes, operação e riscos da versão 1.0;
- regras de contribuição e orientação para agentes de programação;
- backlog priorizado e milestones executáveis para a clínica piloto;
- monorepo executável com frontend Next.js, backend FastAPI, worker Python, contratos compartilhados e testes Playwright;
- PostgreSQL, migrações Alembic, seed fictício idempotente e MinIO por Docker Compose;
- autenticação com cookie `HttpOnly`, CSRF, organizações, papéis básicos e isolamento multiempresa no backend;
- cadastro de clientes, Brand Kit básico e criação provisória de revisor cliente;
- provider mock determinístico e criação de conteúdo sem API paga;
- estados e transições de revisão interna, envio ao cliente, aprovação e correção versionada após feedback;
- notificações internas e audit log para o fluxo vertical;
- painel da agência e portal do cliente em português, responsivos e ligados à API real;
- worker com claim PostgreSQL por `SKIP LOCKED`, lease, timeout, retries, backoff e handlers de e-mail console/provider mock;
- Makefile e scripts para setup, migração, seed, qualidade e E2E;
- CI para Ruff, mypy, pytest, ESLint, TypeScript, Vitest, build, Compose e E2E obrigatório;
- fluxo Playwright com agência e cliente reais do seed, aprovação, notificações, auditoria e verificação móvel;
- criação de revisão pela agência com feedback do cliente e alteração real de título, legenda ou CTA.
- convites de organização e recuperação de senha com token expirável, hash e uso único;
- gestão de membros e matriz central de capacidades para os oito papéis da versão 1.0;
- serviços, públicos, objetivos e presets visuais completos por cliente;
- biblioteca privada de mídia com upload de imagem validado e URLs assinadas;
- estratégia mensal versionada, revisão, aprovação, planos e calendário editorial;
- geração determinística de prompts visuais com provider mock;
- conteúdo ligado a estratégia, pauta, preset, catálogos e mídia;
- aprovações independentes de texto e imagem e revisão visual imutável pelo designer;
- Mailpit local e jobs SMTP para convites, recuperação, estratégia e conteúdo;
- registro manual e idempotente de publicação, sem integração social;
- relatório por período com exportação simples e indicação das métricas indisponíveis;
- seed ampliado com dados fictícios da jornada da Fase 2.

### Corrigido

- inicialização do Compose para aplicar migrações e seed antes de disponibilizar a API;
- healthchecks da API, frontend e worker, incluindo proxy runtime do frontend;
- encaminhamento de cookies de sessão e CSRF pelo proxy `/api/v1`;
- credencial demo do cliente padronizada entre backend, Compose e E2E;
- asserção do audit log no E2E e alinhamento das rotas com o contrato real;
- imagem Playwright atualizada para versão sem os alertas de segurança encontrados;
- contexto Docker do worker reduzido para não copiar caches e dependências locais;
- rascunhos e revisão interna removidos das consultas do portal do cliente;
- notas internas do Brand Kit redigidas para papéis externos;
- pedido de alteração deixou de criar uma cópia fictícia atribuída ao cliente;
- envio concorrente protegido por lock e unicidade da aprovação por versão;
- provider mock limita título e CTA ao contrato persistido no PostgreSQL.
- memberships ativas do portal agora exigem empresa válida no banco e na sessão;
- arquivar um cliente revoga o portal e remove seus conteúdos das rotas ativas;
- `VIEWER` deixou de receber acesso divergente ao audit log;
- pedido de alteração não pode reenviar a mesma versão e colidir com a aprovação anterior;
- rate limit de login separa identidade e origem e mantém armazenamento local limitado;
- CORS curinga e `SameSite` inválido são recusados pela configuração de produção;
- imagem do worker deixou de incorporar caches, ambientes locais e metadados editáveis;
- setup e E2E passaram a exigir também o healthcheck do worker e proteger `.env` local com modo restrito quando suportado.
- provisionamento direto de revisor ficou restrito a desenvolvimento/teste e trata duplicidade concorrente sem erro interno.
- dashboard móvel deixou de expandir horizontalmente quando conteúdos têm títulos longos.
- troca de senha passou a revogar sessões anteriores por versão de sessão;
- vínculos de conteúdo e arquivos agora validam organização e cliente em todas as referências;
- decisões parciais não aprovam o conteúdo até texto e imagem estarem aprovados;
- confirmação repetida de publicação manual não duplica evento nem altera o registro original.
- portal cliente deixou de receber prompts, snapshots, notas e IDs internos;
- jobs de notificação passaram a guardar somente a referência e revalidar o
  acesso do destinatário antes do SMTP;
- `DESIGNER` ficou restrito a preset, mídia, prompt e revisão visual, sem geração
  textual nem edição integral do Brand Kit;
- mudanças de papel, escopo ou suspensão revogam definitivamente sessões antigas;
- capacidades de audit log e notificação passaram a ser aplicadas nas próprias rotas;
- URL assinada de mídia passou a gerar evento auditável sem persistir URL ou chave;
- conteúdo ligado diretamente a estratégia preserva a versão exata, e imagem
  sem mídia vinculada não pode ser aprovada.
- endpoints legados de decisão conjunta foram removidos; texto e imagem agora
  passam exclusivamente pelos contratos granulares;
- o seed passou a gravar e reparar uma imagem fictícia real no storage privado,
  mantendo o vínculo visual idempotente;
- configuração local deixou de anunciar variáveis sem efeito e separou a porta
  SMTP interna da porta publicada do Mailpit;
- o E2E passou a exigir que a imagem privada tenha sido efetivamente carregada,
  além de verificar a presença do elemento visual.
- aprovações visuais legadas sem mídia deixaram de herdar um estado aprovado;
  a migration cancela o estado inválido, devolve o conteúdo para revisão e
  registra a normalização no audit log;
- a área de equipe deixou de criar uma coluna móvel implícita maior que 360 px;
- localizadores e sincronização do E2E foram alinhados aos labels acessíveis e
  ao carregamento assíncrono dos vínculos de mídia.

### Validação

- 136 testes do backend aprovados;
- 28 testes do worker aprovados;
- 30 testes do frontend aprovados;
- 7 cenários E2E aprovados, incluindo identidade, fluxo editorial completo e
  verificações em viewport de 360 px;
- Ruff, mypy, ESLint, TypeScript e builds aprovados;
- auditorias de dependências executadas sem vulnerabilidade pendente no gate adotado;
- Docker Compose validado com serviços de aplicação, banco, storage e profile de teste.
- migrations validadas de `base` a `0008`, com ciclo completo em banco isolado,
  compatibilidade de dados legados e ausência de diferença para os modelos;
- seed fictício executado duas vezes sem duplicar registros ou perder o objeto
  de mídia privado.
- Fase 2 integrada à `main` por squash em 2026-07-16; stack, migration `0008`,
  `make status`, `make test`, `make e2e` e CI foram revalidados após o merge.

### Segurança

- isolamento multiempresa e autorização implementados e cobertos por testes no backend;
- sessão em cookie `HttpOnly`, CSRF e hash de senha por biblioteca mantida;
- tentativas de login limitadas por origem e identidade, com resposta `Retry-After`;
- imagens de backend e worker executadas como usuário sem privilégios e sem dependências de teste;
- produção rejeita segredo conhecido, cookie inseguro, origem CORS curinga, `SameSite` inválido e seed demo;
- proibição de segredos no repositório e de uso cruzado de dados entre clientes;
- revisão profissional para conteúdo veterinário ou de saúde preservada como requisito; o bloqueio automatizado completo ainda é pendente.
- tokens puros de convite e recuperação não são persistidos nem enviados em query string;
- arquivos são normalizados para remover metadados, recebem chave aleatória por tenant e permanecem privados;
- e-mails e logs omitem senha, token, prompt, legenda e comentário de aprovação.
- e-mails operacionais são resolvidos por notificação e membership ativa no worker.
- criação de notificação e tentativa de entrega por e-mail possuem eventos de
  auditoria próprios, com metadados mínimos e sem corpo ou destinatário.

### Limites conhecidos

- a versão 1.0 não publica automaticamente em redes sociais;
- Meta Ads, Google Ads, WhatsApp oficial e gasto automático permanecem fora do escopo;
- providers externos e Hermes são opcionais; o funcionamento local depende apenas do provider mock;
- preferências e resumos de notificação, painel de providers/Hermes e Centro de Integrações ainda não foram entregues;
- controles operacionais de LGPD, bloqueio profissional automatizado, backup/restauração e hardening final permanecem;
- a conclusão da Fase 2 não representa, sozinha, a aprovação da release 1.0.

<!-- Ao criar uma versão, mova os itens de "Não lançado" para uma seção como:
## [0.1.0] - AAAA-MM-DD
Use apenas mudanças verificadas e não antecipe funcionalidades ainda não entregues.
-->
