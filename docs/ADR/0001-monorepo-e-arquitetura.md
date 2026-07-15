# ADR-0001 — Monorepo e monólito modular com worker separado

- **Status:** aceita
- **Data:** 2026-07-15
- **Decisores:** equipe DevMark GrowthOS
- **Escopo:** fundação da versão 1.0

## Contexto

O DevMark GrowthOS é um produto novo e separado do site institucional DevMark IA. Precisa entregar rapidamente um fluxo real entre agência e cliente, sem perder isolamento multiempresa, auditabilidade, providers substituíveis e capacidade de executar tarefas assíncronas.

O time precisa desenvolver e versionar frontend, API, worker, contratos, infraestrutura, documentação e testes coordenados. A versão 1.0 será operada por uma clínica piloto e não justifica a complexidade operacional de microserviços, broker obrigatório ou diversos repositórios.

Ao mesmo tempo, concentrar todas as regras em um único framework full stack aumentaria o acoplamento com a interface e dificultaria os providers Python/Hermes, jobs e futuros consumidores da API.

## Decisão

Adotar um **monorepo independente** chamado `DevMark-GrowthOS`, sem alterar ou incorporar o repositório institucional `DevMark-ia`.

Dentro do monorepo:

- `frontend`: Next.js, TypeScript, Tailwind CSS e componentes acessíveis;
- `backend`: FastAPI, Pydantic, SQLAlchemy 2 e Alembic;
- `worker`: processo Python separado que reutiliza domínio/serviços e executa jobs;
- `shared`: contratos, enums e tipos gerados, sem regra de infraestrutura;
- PostgreSQL como banco transacional e fila inicial por tabela `jobs`;
- armazenamento compatível com S3, usando MinIO localmente;
- providers por portas/adaptadores, com mock obrigatório e Hermes opcional;
- Docker Compose para o ambiente local e CI para lint, tipos, testes e build.

O backend será um **monólito modular**. Módulos de identidade, organizações, clientes, marca, conteúdo, aprovações, notificações, providers, jobs e auditoria têm limites internos claros, mas são implantados inicialmente como uma API.

Frontend, API e worker são processos/contêineres separados e podem escalar de forma independente. Eles são construídos a partir do mesmo commit e não são microserviços autônomos.

## Detalhes obrigatórios da decisão

1. Regras de domínio e autorização ficam no backend, nunca somente no frontend.
2. Toda entidade de tenant tem vínculo explícito com a organização; empresas limitam o acesso do cliente.
3. Conteúdo revisado é versionado e aprovação aponta para versão imutável.
4. Jobs são persistidos e reivindicados de forma concorrente segura; handlers permanecem desacoplados para uma fila futura.
5. A sessão usa implementação mantida, cookie `HttpOnly` e proteção CSRF quando aplicável; criptografia/sessão não é criada artesanalmente.
6. Integrações externas passam por adaptadores; nenhuma chamada real de publicação, Ads ou WhatsApp entra na 1.0.
7. O caminho principal funciona sem API paga por meio do provider mock.
8. Migrations são a fonte de verdade do schema; OpenAPI é a fonte do contrato HTTP.

## Motivos

- Mudanças de contrato, migrations, interface e testes podem ser revisadas em conjunto.
- Uma única base de domínio evita duplicação entre API e worker.
- FastAPI/Python combina com providers e Hermes; Next.js oferece boa experiência mobile e separação clara do portal.
- O monólito modular reduz deploys, falhas distribuídas e custo operacional durante a validação.
- PostgreSQL já atende dados, auditoria e volume inicial de jobs, mantendo Redis opcional.
- Portas/adaptadores reduzem dependência de fornecedores de IA, e-mail, imagem e storage.

## Consequências positivas

- configuração local e onboarding de desenvolvimento mais simples;
- mudanças ponta a ponta atômicas em um pull request;
- transações consistentes entre conteúdo, aprovação, notificação interna, job e auditoria;
- menos infraestrutura para operar na clínica piloto;
- teste de isolamento e fluxo completo no mesmo repositório;
- possibilidade de separar componentes depois com base em métricas reais.

## Consequências negativas e mitigação

| Consequência | Mitigação |
| --- | --- |
| CI pode ficar mais lento conforme o repositório cresce | Detecção de caminhos, cache e jobs paralelos sem pular testes de integração necessários |
| Módulos podem se acoplar por conveniência | Dependências orientadas para domínio, interfaces explícitas e revisão arquitetural |
| Banco compartilhado aumenta alcance de uma query errada | Escopo obrigatório, FKs compostas, testes negativos e futura avaliação de RLS |
| Tabela de jobs tem limites de throughput | Lotes pequenos, índices, lease/locking e métricas; migrar quando houver evidência |
| Dois ecossistemas exigem tooling Node e Python | Docker Compose e comandos documentados na raiz |
| Deploy coordenado pode dificultar evolução incompatível | Migrations compatíveis em etapas e contratos versionados |

## Alternativas consideradas

### Microserviços e repositórios separados desde o início

Rejeitada na 1.0. Exigiria contratos distribuídos, observabilidade, deploy e consistência eventual antes de existir carga que justifique esse custo. A modularidade interna preserva um caminho de extração futuro.

### Aplicação inteira em Next.js

Rejeitada. Simplificaria um runtime, mas acoplaria domínio e jobs ao frontend e não aproveitaria adequadamente o ecossistema Python/Hermes previsto no produto.

### Frontend e backend em repositórios distintos

Rejeitada agora. Aumentaria coordenação para OpenAPI, tipos, fluxo E2E e releases da equipe inicial, sem benefício operacional suficiente.

### Broker Redis/RabbitMQ obrigatório

Adiada. PostgreSQL com jobs persistidos atende o volume inicial e reduz dependências. Os handlers serão escritos para permitir migração sem reescrever regras.

### Integração direta com um único provider de IA

Rejeitada por requisito do produto, custo, disponibilidade, privacidade e risco de lock-in. Providers implementam contratos internos e o mock é sempre suportado.

### Transformar o site institucional no aplicativo

Rejeitada de forma definitiva. Site público e produto têm público, segurança, dados e ciclo de deploy distintos.

## Limites

Esta decisão não autoriza:

- publicação automática;
- Meta Ads, Google Ads ou WhatsApp real;
- gasto financeiro;
- geração automática de vídeo;
- uso cruzado de dados entre clientes;
- microserviços sem nova decisão e evidência.

## Critérios para reavaliar

Criar novo ADR se ocorrer um ou mais destes sinais:

- jobs no PostgreSQL não atendem volume/latência mesmo após índices e tuning;
- um módulo exige escala, segurança ou disponibilidade claramente independente;
- deploys coordenados causam indisponibilidade recorrente;
- equipes autônomas precisam de ciclos de release separados;
- requisito regulatório impõe isolamento físico adicional;
- medições mostram que a divisão reduz mais risco do que adiciona complexidade.

Uma eventual extração deve começar pelo contrato e pelos dados do módulo, preservar `organization_id`, idempotência e auditabilidade, e não interromper o provider mock.

## Relações

- [Arquitetura](../03-arquitetura.md)
- [Modelo de dados](../04-modelo-de-dados.md)
- [Escopo da versão 1.0](../01-escopo-versao-1.md)

