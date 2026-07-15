# Milestones executáveis da versão 1.0

## Como usar este plano

Os milestones são gates sequenciais, não datas prometidas. Um milestone termina somente quando seus critérios de saída têm evidência. Trabalho do próximo milestone pode ser preparado em paralelo, mas não deve esconder falha ou dívida bloqueante no atual.

Estados: `PLANNED`, `IN_PROGRESS`, `DONE` e `BLOCKED`.

| Milestone | Estado inicial | Resultado demonstrável | Depende de |
|---|---|---|---|
| `M0` Documentação e decisões | `PLANNED` | Escopo, arquitetura e plano entendidos por outra pessoa | — |
| `M1` Fundação executável | `PLANNED` | Monorepo sobe e valida código/testes em modo local | `M0` |
| `M2` Identidade e isolamento | `PLANNED` | Login e organização funcionam sem vazamento entre tenants | `M1` |
| `M3` Cliente e Brand Kit | `PLANNED` | Agência cadastra cliente e marca reais | `M2` |
| `M4` Conteúdo mock versionado | `PLANNED` | Agência gera e edita conteúdo sem API paga | `M3` |
| `M5` Fluxo vertical de aprovação | `PLANNED` | Cliente recebe, decide e a equipe é notificada com auditoria | `M4` |
| `M6` Escopo completo da clínica piloto | `PLANNED` | Estratégia, calendário, visual, e-mail, publicação manual e relatório funcionam | `M5` |
| `M7` Hardening e release 1.0 | `PLANNED` | Os 25 critérios finais têm evidência e a release pode ser operada | `M6` |

## Regra comum de saída

Além dos aceites específicos, cada milestone exige:

- itens listados em `DONE`, com dependências concluídas;
- lint, tipos e testes afetados verdes;
- teste negativo de organização e papel nas novas superfícies de dados;
- nenhum segredo, dado real ou dependência de API paga;
- audit log avaliado para toda ação relevante;
- migração, OpenAPI, documentação e changelog atualizados quando aplicável;
- demonstração em português simples contendo o que funciona, o que falta, como testar, riscos e próximo passo;
- commits pequenos e claros, sem misturar mudanças sem relação.

## M0 — Documentação e decisões

**Objetivo:** transformar o prompt mestre em limites, decisões e trabalho executável antes de codificar.

**Entrada:** repositório separado identificado como DevMark GrowthOS; prompt mestre disponível e lido por inteiro.

**Itens do backlog:** `V1-DOC-001`.

**Ordem de execução:**

1. confirmar raiz Git e ausência de vínculo operacional com `bugijo/DevMark-ia`;
2. criar os 14 documentos obrigatórios e o diretório `docs/ADR/`;
3. registrar decisões de stack, tenancy, autenticação, jobs, storage e providers;
4. criar arquivos de governança, backlog e este plano;
5. revisar consistência entre escopo, dados, papéis, fluxos e aceites.

**Critérios de saída:**

- todos os documentos obrigatórios existem e não se contradizem sobre o primeiro fluxo vertical;
- arquitetura escolhida mantém backend como barreira de autorização e provider mock como padrão;
- riscos principais têm prevenção, sinal e resposta;
- itens do backlog têm ID, prioridade, dependência e aceite testável;
- limites de publicação, anúncios e WhatsApp estão explícitos.

**Demonstração:** uma pessoa sem contexto consegue responder o que é o produto, o que entra na v1, como os dados são isolados, qual é o primeiro fluxo e como o sistema será executado.

**Validação:**

```bash
test -f README.md
test -f AGENTS.md
test -f .env.example
test -d docs/ADR
find docs -maxdepth 2 -type f -name '*.md' | sort
git diff --check
```

## M1 — Fundação executável

**Objetivo:** obter uma base reproduzível que compile, migre e rode testes sem serviço pago.

**Entrada:** `M0` concluído e ADRs aceitos.

**Itens do backlog:** `V1-FND-001`, `V1-FND-002`, `V1-FND-003`, `V1-FND-004`, `V1-DAT-001`, `V1-DAT-002`, `V1-DAT-003`, `V1-DAT-004`.

**Ordem de execução:**

1. criar frontend Next.js/TypeScript e backend FastAPI/Python;
2. criar worker Python que usa a tabela de jobs;
3. configurar PostgreSQL, MinIO e redes/volumes do Compose;
4. adicionar configuração validada, logs estruturados, erros e correlation ID;
5. criar primeira migração e seed idempotente fictício;
6. adicionar lint, tipos, testes e CI com cache e serviços de teste;
7. adicionar healthchecks e garantir inicialização determinística.

**Critérios de saída:**

- `docker compose up --build -d` deixa serviços saudáveis em ambiente limpo;
- migrações sobem desde banco vazio e seed pode rodar duas vezes;
- frontend e `/docs` da API respondem;
- worker processa um job de teste e registra sucesso/falha/retry;
- CI e comandos locais de lint, tipos e teste passam sem internet externa;
- `.env.example` basta para iniciar e nenhum segredo está versionado.

**Demonstração:** abrir frontend e OpenAPI, inserir um job fictício, mostrar execução pelo worker e consultar o registro persistido após reiniciar os contêineres.

**Validação:**

```bash
cp -n .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run test
```

## M2 — Identidade e isolamento multiempresa

**Objetivo:** estabelecer quem é o usuário, em qual organização atua e o que pode fazer.

**Entrada:** `M1` concluído; schema e seed reproduzíveis.

**Itens do backlog:** `V1-AUT-001`, `V1-AUT-003`, `V1-AUT-004`, `V1-AUT-005`, `V1-UI-001`, base de `V1-APR-004` para identidade e permissões.

**Ordem de execução:**

1. implementar hash de senha, login, sessão segura e logout com biblioteca mantida;
2. implementar organização, membership e convite;
3. definir capacidades dos oito papéis e aplicá-las nos casos de uso;
4. criar audit log para login relevante, convite, aceite e mudança de papel;
5. criar shell autenticado com navegação por capacidade;
6. testar duas organizações e todos os caminhos de consulta por ID/listagem.

**Critérios de saída:**

- usuário autenticado acessa apenas organizações das quais é membro;
- papel sem capacidade recebe 403 mesmo em requisição direta;
- convite aceito cria membership exatamente na organização esperada;
- alteração de papel e convite são auditados;
- testes negativos não vazam recurso, arquivo, notificação ou log de outro tenant;
- logout/expiração impedem reutilização da sessão conforme a política escolhida.

**Demonstração:** entrar como admin da organização A, convidar revisor, aceitar o convite e provar que ambos não acessam um recurso sem autorização da organização B.

**Validação:**

```bash
docker compose exec backend pytest -m 'auth or tenancy or permissions'
docker compose exec frontend npm run test
docker compose logs --since=5m backend
```

## M3 — Cliente e Brand Kit básico

**Objetivo:** permitir que a agência represente a clínica piloto e sua identidade com dados reais da aplicação.

**Entrada:** `M2` concluído; usuário interno e revisor de cliente disponíveis no seed.

**Itens do backlog:** `V1-DAT-005` na parte necessária, `V1-CLI-001`, `V1-CLI-002`, `V1-BRD-001`, `V1-UI-002`.

**Ordem de execução:**

1. migrar tabelas de cliente e Brand Kit com índices e organização;
2. implementar casos de uso, autorização e API de cliente;
3. implementar Brand Kit básico com validação de campos e regras da marca;
4. vincular responsáveis do cliente aos papéis permitidos;
5. criar formulários mobile first, estados vazios e feedback;
6. adicionar eventos de auditoria e testes cruzados.

**Critérios de saída:**

- `AGENCY_ADMIN` cria e edita clínica da própria organização;
- Brand Kit persiste os campos básicos e é exibido novamente pela API/interface;
- revisor vinculado vê somente sua empresa e não edita campos proibidos;
- duplicidade e entradas inválidas retornam mensagem útil sem alteração parcial;
- cadastro, alteração e vínculo são auditados;
- CAV1-01 e CAV1-04 têm evidência; CAV1-02 e CAV1-03 permanecem demonstráveis pelo fluxo de convite/login.

**Demonstração:** pela interface, criar a “Clínica Veterinária Demo”, preencher identidade básica, sair e entrar como revisor para visualizar somente essa marca.

**Validação:**

```bash
docker compose exec backend pytest -m 'businesses or brand or tenancy'
docker compose exec frontend npm run test
```

## M4 — Conteúdo mock versionado

**Objetivo:** produzir conteúdo persistido, editável e rastreável sem API paga.

**Entrada:** `M3` concluído; cliente e Brand Kit válidos disponíveis.

**Itens do backlog:** `V1-PRV-001`, `V1-PRV-002`, `V1-CNT-003`, `V1-CNT-004`, `V1-UI-003`, continuação de `V1-APR-004`.

**Ordem de execução:**

1. definir contratos de texto, imagem e e-mail fora do domínio;
2. implementar mocks determinísticos com sucesso, atraso e falha controláveis;
3. criar entidades de conteúdo e versão, com estado inicial `DRAFT`;
4. implementar geração mock e editor que sempre preserva histórico;
5. exibir preview, legenda e metadados na interface;
6. auditar criação e versão e testar timeout/erro do provider.

**Critérios de saída:**

- aplicação gera conteúdo coerente com dados fictícios da marca sem chave/rede externa;
- conteúdo contém os campos obrigatórios e nasce em `DRAFT`;
- cada edição cria versão imutável, numerada e atribuída;
- erro do provider não cria conteúdo parcial nem deixa job preso;
- dois tenants não acessam conteúdo ou versões entre si;
- CAV1-08 e CAV1-25 têm evidência.

**Demonstração:** gerar uma legenda mock para a clínica, editar o CTA, comparar versões e mostrar eventos correspondentes no audit log.

**Validação:**

```bash
docker compose exec backend pytest -m 'providers or content or versions'
docker compose exec worker pytest
docker compose exec frontend npm run test
```

## M5 — Primeiro fluxo vertical de aprovação

**Objetivo:** fechar o menor ciclo de negócio completo entre agência e cliente.

**Entrada:** `M4` concluído; usuário interno, cliente, marca e conteúdo versionado disponíveis.

**Itens do backlog:** `V1-APR-001`, `V1-APR-002`, `V1-APR-003`, conclusão de `V1-APR-004`, `V1-NTF-001`, `V1-UI-004`, `V1-TST-001`.

**Ordem de execução:**

1. centralizar estados e transições de conteúdo no domínio;
2. implementar revisão interna e envio da versão atual ao cliente;
3. criar notificação interna e contador de pendências na mesma unidade lógica/outbox definida;
4. implementar portal móvel com preview e ações claras;
5. implementar aprovação, pedido de alteração, comentários e nova versão;
6. notificar a equipe sobre a decisão e registrar toda a linha do tempo;
7. automatizar o cenário ponta a ponta e casos negativos.

**Critérios de saída:**

- fluxo login → organização → cliente → Brand Kit → conteúdo mock → revisão interna → cliente funciona pela interface;
- envio cria uma única notificação mesmo com retry;
- revisor aprova ou pede alteração apenas para a versão atual da própria empresa;
- pedido de alteração cria caminho para nova versão e nova aprovação;
- todas as etapas relevantes aparecem no audit log com ator, organização e versão;
- portal funciona a 360 px e deixa a ação principal visível;
- CAV1-10 a CAV1-14, CAV1-18 a CAV1-20 têm evidência inicial.

**Demonstração:** executar o primeiro fluxo vertical completo com dois logins e mostrar, ao final, a notificação da equipe e a linha do tempo de auditoria.

**Validação:**

```bash
docker compose exec backend pytest -m 'approvals or notifications or audit'
docker compose run --rm e2e --grep 'fluxo vertical'
docker compose exec frontend npm run test
```

**Checkpoint obrigatório ao proprietário:** explicar em português simples o que já funciona, deixar claro que ainda não existe publicação real, ensinar o roteiro de teste e listar riscos antes de ampliar o escopo.

## M6 — Escopo completo da clínica piloto

**Objetivo:** completar as funcionalidades obrigatórias da v1 sobre a fundação já provada.

**Entrada:** `M5` concluído e estável; fluxo vertical protegido por regressão.

**Itens do backlog:** `V1-FND-005`, `V1-AUT-002`, `V1-BRD-002` a `V1-BRD-005`, `V1-PRV-003` a `V1-PRV-005`, `V1-CNT-001`, `V1-CNT-002`, `V1-CNT-005` a `V1-CNT-007`, `V1-APR-005`, `V1-NTF-002`, `V1-NTF-003`, `V1-UI-005`, `V1-UI-006`, `V1-PUB-001`, `V1-RPT-001`, `V1-INT-001`.

**Ordem de execução por fatias:**

1. completar serviços, públicos, objetivos, presets e uploads;
2. gerar estratégia e calendário com o mock;
3. completar ideias, legendas, roteiros, prompts, templates, híbrido e variações;
4. entregar histórico, preferências, e-mail mock, lembretes e recuperação de senha;
5. entregar dashboards, calendário e telas obrigatórias integradas;
6. permitir registro manual de publicação e gerar relatório básico sem inventar métrica;
7. expor Centro de Integrações somente com providers seguros/mock;
8. testar cada fatia sem quebrar o cenário de `M5`.

**Critérios de saída:**

- onboarding aponta e conclui marca, serviços, público, preset, referências e aprovadores;
- estratégia, calendário, conteúdo visual e variações são gerados/geridos com mock;
- notificação por e-mail usa console/mock, retries e preferência do usuário;
- conteúdo aprovado aparece no calendário e pode receber publicação manual auditada;
- relatório usa somente dados existentes e deixa ausências claras;
- todas as telas obrigatórias possuem backend, persistência e estado vazio útil;
- providers reais permanecem opcionais e ações externas proibidas permanecem desligadas;
- CAV1-05 a CAV1-09 e CAV1-15 a CAV1-17 têm evidência.

**Demonstração:** realizar onboarding completo da clínica, gerar estratégia/calendário/peça híbrida mock, aprovar, registrar publicação manual e abrir relatório do período.

**Validação:**

```bash
docker compose exec backend pytest
docker compose exec worker pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run test
docker compose run --rm e2e
```

## M7 — Hardening, operação e release 1.0

**Objetivo:** demonstrar segurança, qualidade, instalação e recuperação suficientes para chamar a clínica piloto de versão 1.0.

**Entrada:** `M6` concluído; escopo funcional congelado, salvo correções.

**Itens do backlog:** `V1-DOC-002`, `V1-SEC-001`, `V1-SEC-002`, `V1-SEC-003`, `V1-OPS-001`, `V1-OPS-002`, `V1-TST-002`, `V1-TST-003`, `V1-REL-001`.

**Ordem de execução:**

1. fechar matriz CAV1-01 a CAV1-25 com testes/evidências;
2. revisar autorização, tenancy, rate limit, sessão, CSRF/CORS, upload e dependências;
3. validar revisão profissional obrigatória para conteúdo sensível;
4. testar acessibilidade, 360/768/1280 px e limites de desempenho local;
5. executar backup/restore e simular falha/retry do worker;
6. testar instalação do zero por pessoa que não implementou o sistema;
7. congelar migrações da release, registrar riscos residuais e plano de rollback;
8. rodar gate final e preparar release/PR.

**Critérios de saída:**

- todos os itens P0 e P1 estão `DONE` sem bloqueio oculto;
- CAV1-01 a CAV1-25 têm evidência aprovada;
- CI, smoke test e instalação limpa passam;
- busca de segredos não encontra credencial e análise de dependência não deixa vulnerabilidade crítica sem resposta;
- teste de duas organizações cobre API, arquivos, worker, relatórios e interface;
- backup restaurado reproduz banco e referências de arquivos esperadas;
- limitações, riscos, operação e rollback estão documentados;
- `CHANGELOG.md` recebe a seção da versão com data somente após a aprovação do gate.

**Demonstração:** uma pessoa nova segue o README em máquina limpa, executa o fluxo completo com dados demo e acompanha audit log, relatório e recuperação documentada sem usar API paga.

**Validação final:**

```bash
docker compose down -v
cp .env.example .env
docker compose build --pull
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
docker compose exec worker pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run test
docker compose run --rm e2e
docker compose ps
git diff --check
```

## Mapa de dependências do fluxo crítico

```text
M0 documentação
  -> M1 monorepo + banco + jobs + CI
    -> M2 login + organização + RBAC + isolamento
      -> M3 cliente + Brand Kit
        -> M4 provider mock + conteúdo + versões
          -> M5 revisão + cliente + notificação + audit log
            -> M6 restante do escopo v1
              -> M7 segurança + operação + aceite final
```

Se um milestone falhar, corrija a base antes de compensar com uma tela ou processo manual não documentado. Em especial, falhas de isolamento, autorização, audit log, migração ou provider mock bloqueiam o avanço.

## Relatório ao concluir cada milestone

Use este formato, em português simples:

```text
Milestone:
O que foi feito:
O que funciona agora:
O que ainda falta:
Como testar:
Testes executados e resultado:
Riscos/limitações:
Próximos passos:
Commits:
```

Não marque o milestone como `DONE` apenas porque o código foi escrito. A demonstração, os testes, a documentação e os critérios de saída fazem parte da entrega.
