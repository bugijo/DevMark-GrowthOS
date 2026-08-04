# DevMark GrowthOS

Central operacional multiempresa da DevMark IA para criar, revisar e aprovar conteúdo com apoio de inteligência artificial e controle humano.

> **Status:** Fase 3 implementada na branch `agent/fechamento-v1` e em validação
> para o piloto. O gate técnico local está verde; a versão 1.0 ainda não está
> declarada concluída porque o aceite independente de instalação (`CAV1-23`)
> depende de uma segunda pessoa seguindo apenas este README.

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
- comparação acessível de título, legenda, CTA, objetivo, prompt visual,
  imagem e estratégia, com autor, data, comentário, lado a lado, alternância e zoom;
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
- dados fictícios e idempotentes para demonstração local;
- onboarding persistido de 15 etapas, retomável e editável;
- preferências e resumos diário/semanal de notificações;
- classificação de conteúdo sensível e revisão profissional obrigatória;
- Centro de Integrações com mock obrigatório, Hermes opcional e configuração
  organizacional sem exposição de segredos;
- consentimentos versionados, inventário de finalidades, retenção, exportação,
  solicitação de exclusão e anonimização auditada;
- diagnóstico, backup verificado, restauração isolada e medição de desempenho.

## O que ainda falta para declarar a versão 1.0

- uma segunda pessoa executar a instalação limpa e o roteiro usando somente o README (`CAV1-23`);
- revisar o Draft PR e confirmar a CI remota;
- antes de dados reais, definir infraestrutura, base legal, contratos, prazos de
  retenção, e-mail transacional e profissional habilitado;
- hospedar segredos em filesystem/secret manager que permita permissões restritas.

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
- Bash 4 ou superior;
- GNU Make;
- GNU coreutils, incluindo `realpath` e `sha256sum`;
- curl;
- Docker Engine 24 ou superior;
- Docker Compose v2;
- pelo menos 4 GiB de memória disponível para o Docker;
- pelo menos 10 GiB livres no disco do clone;
- acesso à internet no primeiro build para baixar imagens e dependências;
- portas locais `1025`, `3000`, `5432`, `8000`, `8025`, `9000` e `9001` livres.

`make setup` e `make e2e` usam Docker e não exigem Python ou Node instalados no host.

Para executar lint e testes unitários diretamente no host, também são necessários:

- Python 3.12 com suporte a `venv` — em Debian/Ubuntu, normalmente o pacote `python3.12-venv`;
- Node.js 22 e npm 10.

## Validação independente CAV1-23

Esta validação deve ser executada por uma pessoa que não participou da
implementação, em um clone novo e sem reutilizar volumes Docker anteriores. O
avaliador deve seguir apenas esta seção e registrar qualquer dúvida ou ajuda
externa necessária. O script opcional não substitui o julgamento do avaliador.

### 1. Requisitos mínimos

- computador Linux, macOS ou Windows com WSL2; no macOS, Bash 4+ e GNU
  coreutils precisam estar instalados e disponíveis no `PATH`;
- Git, Bash 4+, GNU Make, GNU coreutils e curl;
- Docker Engine 24+ com daemon iniciado e Docker Compose v2;
- 4 GiB de memória disponíveis para o Docker e 10 GiB livres no disco;
- internet para o primeiro build;
- portas `1025`, `3000`, `5432`, `8000`, `8025`, `9000` e `9001` livres;
- `ss` (Linux) ou `lsof` (macOS) se usar o verificador opcional.

Python e Node.js não são necessários para `make setup` nem `make e2e`. Eles só
são necessários para `make install`, `make lint` e `make test` no host.

### 2. Clonar exatamente a versão em avaliação

Escolha uma pasta que ainda não contenha `DevMark-GrowthOS` e execute:

```bash
git clone --branch agent/fechamento-v1 --single-branch https://github.com/bugijo/DevMark-GrowthOS.git
cd DevMark-GrowthOS
git status --short --branch
git rev-parse HEAD
```

O `git status` não deve listar arquivos modificados ou novos. Guarde o hash
mostrado por `git rev-parse HEAD` no relatório.

### 3. Criar a configuração local

```bash
cp .env.example .env
chmod 600 .env
git check-ignore .env
```

Não coloque credenciais reais no arquivo. `git check-ignore .env` deve imprimir
`.env`. Em filesystems que não preservam `chmod`, registre o aviso no relatório
e não utilize dados reais.

### 4. Diagnosticar e instalar

Com o Docker iniciado, execute na raiz do clone:

```bash
make setup
make doctor
make status
```

`make setup` constrói as imagens, sobe os serviços, aplica as migrations e
carrega o seed fictício. No diagnóstico final, não deve haver `ERRO`; todos os
serviços abaixo devem aparecer como `healthy` em `make status`:

- `postgres`;
- `minio`;
- `mailpit`;
- `backend`;
- `worker`;
- `frontend`.

Se algo falhar, não altere código nem esconda a saída. Registre o comando, a
mensagem completa e consulte os logs com:

```bash
docker compose logs --no-color backend worker frontend postgres minio mailpit
```

### 5. Acessar e testar manualmente

- frontend: `http://localhost:3000`;
- backend/OpenAPI: `http://localhost:8000/docs`;
- Mailpit: `http://localhost:8025`;
- health do backend: `http://localhost:8000/api/v1/health/ready`.

Credenciais exclusivamente fictícias:

| Papel | E-mail | Senha |
|---|---|---|
| Agência | `admin@devmark.local` | `local-demo-only-change-before-use` |
| Cliente revisor | `client@clinicafeliz.local` | `local-demo-client-only-change-before-use` |

Entre com os dois usuários e execute o [roteiro de teste manual](#roteiro-de-teste-manual).

### 6. Executar os testes essenciais

O teste essencial, sem Python ou Node.js no host, é:

```bash
make e2e
```

Se o host também possuir Python 3.12 com `venv`, Node.js 22 e npm 10:

```bash
make install
make lint
make test
```

Opcionalmente, o avaliador pode executar toda a sequência automatizada desta
seção. Ela grava o log em `.data/cav1-23/`, não corrige falhas e retorna código
diferente de zero se algum check falhar:

```bash
./scripts/cav1-23-check.sh
```

### 7. Desligar ou limpar

Para desligar preservando os dados e volumes:

```bash
make down
```

Depois de salvar as evidências, para apagar deliberadamente todos os volumes
locais do GrowthOS e deixar o ambiente limpo:

```bash
make reset
```

`make reset` é destrutivo somente para os volumes deste projeto. Não o execute
antes de coletar logs ou screenshots necessários.

### 8. Registrar o resultado

Copie [o modelo de relatório](docs/templates/cav1-23-relatorio.md), preencha
todos os campos e anexe ao Draft PR #3 junto com logs ou screenshots. Qualquer
pedido de ajuda externa deve ser registrado, mesmo quando a instalação termina.
Marque `PASS` somente se todos os itens obrigatórios funcionarem sem alteração
de código ou instrução não presente neste README.

Checklist do avaliador:

- [ ] clone novo, branch e commit registrados;
- [ ] requisitos mínimos confirmados;
- [ ] `.env` criado somente a partir de `.env.example` e ignorado pelo Git;
- [ ] `make setup` terminou sem erro;
- [ ] `make doctor` terminou sem `ERRO`;
- [ ] seis serviços aparecem saudáveis em `make status`;
- [ ] frontend, backend e Mailpit abriram no navegador;
- [ ] login de agência e cliente funcionou;
- [ ] roteiro manual foi concluído;
- [ ] `make e2e` passou;
- [ ] desligamento/limpeza e falhas foram registrados;
- [ ] relatório preenchido com resultado `PASS` ou `FAIL` e anexado ao PR.

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

Resultados verificados na Fase 3 devem ser consultados na
[matriz de evidências](docs/18-matriz-evidencias-v1.md), que registra também
qualquer gate ainda bloqueado.

| Área | Resultado |
|---|---:|
| Backend | 209 testes aprovados |
| Worker | 41 testes aprovados |
| Frontend | 52 testes aprovados |
| E2E | 9 cenários aprovados |

Ruff, mypy, ESLint, checagem TypeScript, builds Docker/Next.js e auditorias de
dependências executadas passaram. As migrations foram validadas de `base` até
`0013`, com downgrade/upgrade em banco isolado e atualização de uma base da
Fase 2 em `0008`.

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
