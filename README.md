# DevMark GrowthOS

Central operacional multiempresa da DevMark IA para planejar, produzir, revisar e acompanhar marketing com apoio de inteligência artificial. O produto é coordenado pelo **Growth Agent** e deve ser simples o bastante para equipes e clientes sem conhecimento técnico.

> Status: fundação da versão 1.0 em construção. O primeiro objetivo executável é provar o fluxo completo entre agência e cliente com providers mock, sem depender de API paga.

## Repositório e limites

Este repositório é exclusivo do **DevMark GrowthOS**. O site institucional da DevMark IA vive no repositório separado `bugijo/DevMark-ia` e não deve ser alterado, movido ou incorporado aqui.

Na versão 1.0, nenhuma ação externa sensível é automática. Estão explicitamente fora do escopo inicial:

- publicação direta no Instagram ou Facebook;
- Meta Ads e Google Ads reais;
- alteração ou gasto automático de orçamento;
- WhatsApp oficial;
- geração automática de vídeo;
- cobrança, white label, marketplace e autonomia total.

## Primeiro fluxo vertical

O primeiro incremento utilizável deve permitir:

1. entrar com e-mail e senha;
2. acessar uma organização autorizada;
3. cadastrar um cliente;
4. preencher seu Brand Kit básico;
5. criar conteúdo com o provider mock;
6. enviar o conteúdo para revisão interna e depois para o cliente;
7. o cliente aprovar ou pedir alteração;
8. gerar uma notificação interna;
9. registrar todas as ações relevantes no audit log.

Esse fluxo deve usar backend, banco e regras reais. Telas sem integração não contam como entrega.

## Tecnologias

- **Frontend:** Next.js, TypeScript e Tailwind CSS, com interface em português do Brasil, acessível e mobile first.
- **Backend:** FastAPI, Python, Pydantic, SQLAlchemy e Alembic, com API REST e OpenAPI.
- **Banco:** PostgreSQL, com vínculo explícito à organização e migrações versionadas.
- **Worker:** processo Python com tabela de jobs no PostgreSQL, retries, timeout e logs; fila dedicada fica preparada para uma versão posterior.
- **Arquivos:** armazenamento compatível com S3; MinIO no desenvolvimento local.
- **IA e imagens:** contratos de provider e adaptadores substituíveis; provider mock ativo por padrão e Hermes opcional.
- **Execução:** Docker Compose para frontend, backend, worker, banco e armazenamento local.
- **Qualidade:** lint, checagem de tipos, testes unitários, de integração e ponta a ponta.

## Estrutura

```text
DevMark-GrowthOS/
├── frontend/          # painel da agência e portal do cliente
├── backend/           # API, domínio, serviços e adaptadores
├── worker/            # execução de jobs assíncronos
├── shared/            # contratos e tipos compartilhados, quando aplicável
├── infra/             # Docker e configuração operacional
├── docs/              # produto, arquitetura, segurança e decisões
├── scripts/           # automações locais reproduzíveis
├── tests/             # integração e testes ponta a ponta
├── .github/           # integração contínua
├── docker-compose.yml
└── .env.example
```

O backend deve separar regras de domínio, casos de uso e infraestrutura. O frontend nunca é a única barreira de autorização. Toda consulta multiempresa precisa ser limitada pela organização do usuário no backend.

## Pré-requisitos

Forma recomendada:

- Git;
- Docker Engine 24 ou superior;
- Docker Compose v2.

Para executar serviços fora de contêineres, use também Node.js 22, npm 10 e Python 3.12. As versões efetivas devem permanecer fixadas nos arquivos do projeto.

## Execução local

O contrato de execução local da fundação é:

```bash
cp .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
```

Depois que os serviços estiverem saudáveis:

- frontend: `http://localhost:3000`;
- API: `http://localhost:8000`;
- documentação OpenAPI: `http://localhost:8000/docs`;
- console do MinIO: `http://localhost:9001`.

Para acompanhar a aplicação:

```bash
docker compose logs -f backend worker frontend
```

Para encerrar sem apagar os dados locais:

```bash
docker compose down
```

Use `docker compose down -v` somente quando quiser remover deliberadamente os volumes de desenvolvimento.

## Migrações, qualidade e testes

Com a stack em execução, o contrato esperado é:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run test
docker compose run --rm e2e
```

Durante a fundação, algum comando pode ficar indisponível até o respectivo serviço ser criado. O milestone só pode ser encerrado depois de o comando correspondente existir e passar.

## Dados de demonstração e providers

O ambiente local usa `AI_PROVIDER=mock`, `IMAGE_PROVIDER=mock` e entrega de e-mail em modo de console. Isso permite testar o produto sem chave externa e sem enviar mensagens reais. Dados de demonstração são fictícios e nunca devem conter informação clínica, pessoal ou comercial real.

Providers remotos e Hermes são opcionais. Adicioná-los exige um adaptador, configuração por ambiente, isolamento por organização, tratamento de falhas e testes de contrato. Chaves e tokens nunca entram no Git.

## Segurança essencial

- toda entidade de negócio multiempresa possui `organization_id` ou vínculo equivalente verificável;
- autorização e isolamento são validados no backend;
- mudanças de permissão, aprovações, versões e ações relevantes entram no audit log;
- conteúdo veterinário ou de saúde exige revisão profissional antes da aprovação final;
- uploads são validados por tipo e tamanho;
- segredos ficam apenas em variáveis de ambiente ou cofre apropriado;
- dados de um cliente nunca alimentam sugestões para outro sem autorização explícita.

Consulte [AGENTS.md](AGENTS.md) antes de alterar código e [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir uma contribuição.

## Documentação

A documentação principal fica em `docs/`, incluindo visão, escopo, roadmap, arquitetura, modelo de dados, fluxos, segurança, testes, operação, riscos e decisões arquiteturais.

Planejamento executável:

- [Backlog da versão 1.0](docs/backlog/versao-1.md)
- [Milestones da versão 1.0](docs/milestones/versao-1.md)

O produto segue versionamento semântico. Mudanças relevantes são registradas em [CHANGELOG.md](CHANGELOG.md).
