# DevMark GrowthOS

Central operacional multiempresa da DevMark IA para criar, revisar e aprovar conteúdo com apoio de inteligência artificial e controle humano.

> **Status:** fundação concluída e Fase 2 da versão 1.0 implementada e validada
> nesta branch. Identidade,
> planejamento, visual, conteúdo, aprovação, e-mail local, publicação manual e
> relatório funcionam com banco real e providers mock. A versão 1.0 só será
> declarada pronta depois do gate de hardening e operação.

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
- organização, matriz completa dos oito papéis e isolamento de dados no backend;
- convites por e-mail com token expirável e de uso único;
- recuperação de senha sem enumeração de conta e invalidação de sessões antigas;
- gestão de membros, papéis, escopo por cliente e suspensão de acesso;
- cadastro de cliente e Brand Kit básico;
- serviços, públicos, objetivos e presets visuais completos por cliente;
- biblioteca privada de mídia com upload validado e URL assinada curta;
- estratégia mensal versionada, revisão interna, decisão do cliente e histórico;
- planos e calendário editorial consultável por mês ou semana;
- provider de texto mock determinístico, sem chave ou API paga;
- prompt visual mock determinístico a partir do Brand Kit e preset;
- conteúdo ligado a estratégia, plano, pauta, preset, catálogos e mídia;
- histórico imutável de versões textuais e visuais;
- fluxo `DRAFT → INTERNAL_REVIEW → CLIENT_REVIEW → APPROVED`;
- aprovação independente de texto e imagem, com correção versionada após feedback;
- notificações internas para cliente e equipe;
- e-mails locais capturados pelo Mailpit, com worker, retries e idempotência;
- registro manual de publicação, sem chamada a rede social;
- relatório por período com dados persistidos e métricas indisponíveis explícitas;
- audit log das etapas relevantes;
- portal responsivo em português, incluindo aprovação em viewport móvel;
- worker PostgreSQL com claim seguro, retries, backoff, timeout e handlers mock/console;
- CI para lint, tipos, testes, builds, Compose e E2E obrigatório;
- dados fictícios e idempotentes para demonstração local.

## O que ainda falta para a versão 1.0

A Fase 2 cobre a operação solicitada, mas não substitui o gate final. Permanecem:

- checklist consolidado de onboarding e comparação visual de versões;
- preferências, lembretes e resumos de notificação;
- painel administrativo de providers e Hermes opcional;
- controles operacionais de LGPD para exportação/exclusão;
- bloqueio automatizado de revisão profissional para conteúdo sensível;
- ensaio documentado de backup/restauração, desempenho e acessibilidade ampliada;
- evidência final dos 25 critérios, instalação limpa e decisão de release.

Consulte o [backlog](docs/backlog/versao-1.md) e os [milestones](docs/milestones/versao-1.md) para a sequência restante.

## Tecnologias

- **Frontend:** Next.js, React, TypeScript e Tailwind CSS, mobile first.
- **Backend:** FastAPI, Python, Pydantic, SQLAlchemy e Alembic.
- **Banco:** PostgreSQL com migrações e vínculo explícito à organização.
- **Worker:** Python e tabela de jobs PostgreSQL com `FOR UPDATE SKIP LOCKED`.
- **Arquivos:** storage S3 compatível e MinIO local, privado, com upload seguro e URL assinada.
- **E-mail local:** SMTP capturado no Mailpit, sem entrega para a internet.
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
- caixa de e-mail local: `http://localhost:8025`.

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
4. Confira os catálogos, o preset, a estratégia e o calendário fictícios do seed.
5. Envie um convite em **Equipe** e abra a mensagem em `http://localhost:8025`.
6. Faça upload de uma imagem em **Mídia** e crie um conteúdo vinculado ao planejamento.
7. Envie o conteúdo para revisão interna e depois para o cliente.
8. Saia e entre como `client@clinicafeliz.local`.
9. Abra a pendência e decida texto e imagem separadamente.
10. Entre novamente como agência, registre a publicação manual e abra o relatório.
11. Confira notificações, e-mails locais e registros de auditoria.

O cliente demo já possui revisor vinculado para o caminho rápido. Convites são o
fluxo normal para novos acessos; a criação direta de revisor continua disponível
somente como compatibilidade de desenvolvimento/teste e é bloqueada em produção.

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

Resultados verificados no gate final da Fase 2:

| Área | Resultado |
|---|---:|
| Backend | 136 testes aprovados |
| Worker | 28 testes aprovados |
| Frontend | 30 testes aprovados |
| E2E | 7 cenários aprovados |

Ruff, mypy, ESLint, checagem TypeScript, builds Docker/Next.js e auditorias de
dependências executadas passaram. As migrations foram validadas de `base` até
`0008`, com downgrade/upgrade em banco isolado, atualização de uma base da
fundação e seed executado duas vezes sem duplicação.

## Providers e segurança

O ambiente local força texto/imagem em modo mock, Hermes desligado e e-mail no
Mailpit local. Nenhuma publicação, mensagem ou gasto externo é realizado.

- autorização e isolamento são validados no backend;
- senhas usam biblioteca mantida e não são armazenadas em claro;
- sessão, CSRF e escopo da organização são verificados nas mutações;
- o portal não recebe rascunhos, revisão interna, notas, prompts ou snapshots internos;
- configuração de produção insegura e seed demo em produção falham no início;
- jobs carregam organização, usam lease transacional e revalidam o destinatário
  ativo antes do SMTP;
- segredos ficam fora do Git;
- dados demo não contêm informação clínica real;
- conteúdo veterinário ou de saúde continua sujeito a revisão profissional.

Providers remotos e canais reais só podem ser adicionados com adaptador,
autorização, isolamento, logs seguros e testes.

## Documentação

A documentação principal fica em `docs/`, incluindo visão, escopo, roadmap, arquitetura, modelo de dados, fluxos, segurança, testes, operação, riscos e ADRs.

Leia [AGENTS.md](AGENTS.md) antes de alterar código, [CONTRIBUTING.md](CONTRIBUTING.md) antes de contribuir e [CHANGELOG.md](CHANGELOG.md) para mudanças verificadas.
