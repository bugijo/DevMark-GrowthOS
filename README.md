# DevMark GrowthOS

Central operacional multiempresa da DevMark IA para criar, revisar e aprovar conteúdo com apoio de inteligência artificial e controle humano.

> **Status:** primeiro ciclo executável concluído. O fluxo vertical mínimo funciona de ponta a ponta com provider mock, banco real, frontend, backend, worker, notificações e audit log. Isso ainda **não** significa que a versão 1.0 esteja pronta.

## Repositório e limites

Este repositório é exclusivo do **DevMark GrowthOS**. O site institucional da DevMark IA vive no repositório separado `bugijo/DevMark-ia` e não deve ser alterado, movido ou incorporado aqui.

Continuam fora da versão 1.0:

- publicação automática no Instagram ou Facebook;
- Meta Ads e Google Ads reais;
- alteração ou gasto automático de orçamento;
- WhatsApp oficial;
- geração automática de vídeo;
- cobrança, white label, marketplace e autonomia total.

## O que funciona agora

- stack local com frontend, backend, worker, PostgreSQL e MinIO por Docker Compose;
- login e logout com sessão em cookie `HttpOnly`, proteção CSRF e limite de tentativas;
- organização, papéis básicos e isolamento de dados no backend;
- cadastro de cliente e Brand Kit básico;
- criação provisória de revisor cliente no ambiente atual;
- provider de texto mock determinístico, sem chave ou API paga;
- criação de conteúdo e histórico de versões;
- fluxo `DRAFT → INTERNAL_REVIEW → CLIENT_REVIEW → APPROVED`;
- pedido de alteração com feedback, edição real e preservação da versão anterior;
- notificações internas para cliente e equipe;
- audit log das etapas relevantes;
- portal responsivo em português, incluindo aprovação em viewport móvel;
- worker PostgreSQL com claim seguro, retries, backoff, timeout e handlers mock/console;
- CI para lint, tipos, testes, builds, Compose e E2E obrigatório;
- dados fictícios e idempotentes para demonstração local.

## O que ainda falta para a versão 1.0

O primeiro ciclo prova a fundação e a aprovação, mas o escopo obrigatório ainda possui lacunas:

- convite seguro, de uso único, e recuperação de senha;
- gestão completa de memberships, papéis e onboarding;
- serviços, públicos e objetivos como módulos completos;
- presets visuais;
- estratégia e calendário editorial;
- geração de ideias, roteiros e variações além do fluxo mock mínimo;
- imagens por template/híbrido, upload seguro e biblioteca de mídia;
- configuração administrativa de providers e Hermes opcional;
- entrega real de e-mail, preferências, lembretes e resumos; hoje há somente console/mock;
- registro manual de publicação;
- relatórios básicos e Centro de Integrações;
- controles operacionais completos de LGPD, backup/restauração e hardening final;
- fechamento dos 25 critérios de aceite da versão 1.0.

Consulte o [backlog](docs/backlog/versao-1.md) e os [milestones](docs/milestones/versao-1.md) para a sequência restante.

## Tecnologias

- **Frontend:** Next.js, React, TypeScript e Tailwind CSS, mobile first.
- **Backend:** FastAPI, Python, Pydantic, SQLAlchemy e Alembic.
- **Banco:** PostgreSQL com migrações e vínculo explícito à organização.
- **Worker:** Python e tabela de jobs PostgreSQL com `FOR UPDATE SKIP LOCKED`.
- **Arquivos:** contrato S3 compatível e MinIO local; o upload de produto ainda será implementado.
- **Providers:** abstrações substituíveis, com mock como padrão e sem integração paga.
- **Qualidade:** Ruff, mypy, ESLint, TypeScript, Vitest, pytest e Playwright.

## Estrutura

```text
DevMark-GrowthOS/
├── frontend/          # painel da agência e portal do cliente
├── backend/           # API, domínio, persistência e migrações
├── worker/            # processamento assíncrono
├── shared/            # contratos compartilhados versionados
├── infra/             # decisões e configuração operacional futura
├── docs/              # produto, arquitetura, segurança e decisões
├── scripts/           # automações reproduzíveis
├── tests/e2e/         # fluxo vertical Playwright
├── .github/           # CI e template de pull request
├── docker-compose.yml
└── Makefile
```

O frontend nunca é a única barreira de autorização. Toda consulta multiempresa precisa ser limitada e autorizada no backend.

## Pré-requisitos

Para subir e testar o produto por Docker:

- Git;
- GNU Make;
- curl;
- Docker Engine 24 ou superior;
- Docker Compose v2.

`make setup` e `make e2e` usam Docker e não exigem Python ou Node instalados no host.

Para executar lint e testes unitários diretamente no host, também são necessários:

- Python 3.12 com suporte a `venv` — em Debian/Ubuntu, normalmente o pacote `python3.12-venv`;
- Node.js 22 e npm 10.

## Subir o sistema

Na raiz do repositório:

```bash
make setup
```

Esse comando cria `.env` a partir de `.env.example` quando necessário, valida o Compose, constrói e inicia os serviços, aplica as migrações e carrega o seed fictício.

Verifique o estado:

```bash
make status
```

Endereços locais:

- aplicação: `http://localhost:3000`;
- API: `http://localhost:8000`;
- OpenAPI: `http://localhost:8000/docs`;
- API health: `http://localhost:8000/api/v1/health`;
- frontend health: `http://localhost:3000/api/health`;
- console do MinIO: `http://localhost:9001`.

Para acompanhar logs ou encerrar:

```bash
make logs
make down
```

`make reset` apaga deliberadamente os volumes locais. Use somente quando quiser perder os dados de desenvolvimento.

## Credenciais de demonstração

As credenciais abaixo são públicas, fictícias e exclusivas do ambiente local:

| Papel | E-mail | Senha |
|---|---|---|
| Agência | `admin@devmark.local` | `local-demo-only-change-before-use` |
| Cliente revisor | `client@clinicafeliz.local` | `local-demo-client-only-change-before-use` |

Nunca reutilize essas senhas em homologação, produção ou conta real.

## Roteiro de teste manual

1. Execute `make setup` e abra `http://localhost:3000`.
2. Entre como agência com `admin@devmark.local`.
3. Confira a organização e o cliente fictício **Clínica Veterinária Demo**. O cadastro de novos clientes e a edição do Brand Kit também estão disponíveis.
4. No cliente demo, crie um conteúdo com o provider mock.
5. Envie o conteúdo para revisão interna e depois para o cliente.
6. Saia e entre como `client@clinicafeliz.local`.
7. Abra a pendência e aprove ou peça alteração.
8. Entre novamente como agência e confira a decisão em Notificações e Logs.

O cliente demo já possui revisor vinculado. Para testar rapidamente a aprovação, use esse cliente; o fluxo atual de criação direta de revisor existe somente em `development/test`, fica bloqueado em produção e será substituído por convite seguro.

## Qualidade e testes

Para instalar ferramentas locais de desenvolvimento:

```bash
make install
```

Esse comando cria `.venv`, instala backend/worker e executa `npm ci`. Ele requer Python 3.12 com `venv`, Node.js 22 e npm.

Depois:

```bash
make lint
make test
```

O E2E usa somente Docker e pode ser executado independentemente da instalação local:

```bash
make e2e
```

Resultados verificados no primeiro ciclo:

| Área | Resultado |
|---|---:|
| Backend | 46 testes aprovados |
| Worker | 7 testes aprovados |
| Frontend | 15 testes aprovados |
| E2E | 3 cenários aprovados |

Ruff, mypy, ESLint, checagem TypeScript, builds Docker/Next.js e auditorias de dependências executadas passaram.

## Providers e segurança

O ambiente local força texto/imagem em modo mock, Hermes desligado e e-mail em console. Nenhuma publicação, mensagem ou gasto externo é realizado.

- autorização e isolamento são validados no backend;
- senhas usam biblioteca mantida e não são armazenadas em claro;
- sessão, CSRF e escopo da organização são verificados nas mutações;
- o portal não recebe rascunhos, revisão interna ou notas internas da marca;
- configuração de produção insegura e seed demo em produção falham no início;
- jobs carregam organização e usam lease transacional;
- segredos ficam fora do Git;
- dados demo não contêm informação clínica real;
- conteúdo veterinário ou de saúde continua sujeito a revisão profissional.

Providers remotos, uploads e canais reais só podem ser adicionados com adaptador, autorização, isolamento, logs seguros e testes.

## Documentação

A documentação principal fica em `docs/`, incluindo visão, escopo, roadmap, arquitetura, modelo de dados, fluxos, segurança, testes, operação, riscos e ADRs.

Leia [AGENTS.md](AGENTS.md) antes de alterar código, [CONTRIBUTING.md](CONTRIBUTING.md) antes de contribuir e [CHANGELOG.md](CHANGELOG.md) para mudanças verificadas.
