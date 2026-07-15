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

### Validação

- 28 testes do backend aprovados;
- 7 testes do worker aprovados;
- 15 testes do frontend aprovados;
- 3 cenários E2E aprovados, incluindo o fluxo completo pela interface;
- Ruff, mypy, ESLint, TypeScript e builds aprovados;
- auditorias de dependências executadas sem vulnerabilidade pendente no gate adotado;
- Docker Compose validado com serviços de aplicação, banco, storage e profile de teste.

### Segurança

- isolamento multiempresa e autorização implementados e cobertos por testes no backend;
- sessão em cookie `HttpOnly`, CSRF e hash de senha por biblioteca mantida;
- tentativas de login limitadas por origem e identidade, com resposta `Retry-After`;
- imagens de backend e worker executadas como usuário sem privilégios e sem dependências de teste;
- produção rejeita segredo conhecido, cookie inseguro e seed demo;
- proibição de segredos no repositório e de uso cruzado de dados entre clientes;
- revisão profissional para conteúdo veterinário ou de saúde preservada como requisito; o bloqueio automatizado completo ainda é pendente.

### Limites conhecidos

- a versão 1.0 não publica automaticamente em redes sociais;
- Meta Ads, Google Ads, WhatsApp oficial e gasto automático permanecem fora do escopo;
- providers externos e Hermes são opcionais; o funcionamento local depende apenas do provider mock;
- convite seguro, recuperação de senha, presets, estratégia, calendário, imagens/upload, e-mail real, publicação manual e relatórios ainda não foram entregues;
- o primeiro ciclo executável não representa a conclusão da versão 1.0.

<!-- Ao criar uma versão, mova os itens de "Não lançado" para uma seção como:
## [0.1.0] - AAAA-MM-DD
Use apenas mudanças verificadas e não antecipe funcionalidades ainda não entregues.
-->
