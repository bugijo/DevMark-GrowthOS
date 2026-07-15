# ADR 0002 — Isolamento multiempresa

- **Status:** Aceita
- **Data:** 2026-07-15
- **Decisão relacionada:** arquitetura e modelo de dados da versão 1.0

## Contexto

O GrowthOS atende a DevMark IA e vários clientes. O impacto de um acesso cruzado é alto: Brand Kits, conteúdos, aprovações, usuários, providers e arquivos de uma empresa não podem ser vistos ou usados por outra.

Filtros do frontend não constituem segurança. Também não basta adicionar `organization_id` às tabelas se consultas, jobs, cache, arquivos e audit log puderem ignorá-lo.

Precisamos de uma solução simples para a versão 1.0, compatível com PostgreSQL e FastAPI, que permita a uma pessoa da agência operar clientes autorizados sem criar um bypass global implícito.

## Decisão

`organization` será a fronteira principal de tenant. Toda entidade multiempresa terá `organization_id` obrigatório e imutável durante sua vida normal.

Uma `business` representa a empresa/marca operada dentro dessa fronteira. Quando uma organização puder conter mais de uma empresa, o acesso do cliente também será limitado por `business_id` ou concessão explícita equivalente. Organização nunca será inferida apenas do negócio enviado no payload.

### Contexto autenticado

A API cria um `ActorContext` (o contexto autenticado do tenant) a partir de:

- usuário autenticado;
- membership ativa;
- organização selecionada entre as memberships autorizadas;
- papel;
- escopo de empresa, quando aplicável.

Identificadores recebidos por URL, header ou body são validados contra esse contexto. Eles ajudam a selecionar o recurso, mas não concedem acesso.

### Acesso da agência

Usuários da agência recebem memberships explícitas nas organizações que operam. Dentro de cada organização, o papel e as concessões de empresa determinam o alcance. `AGENCY_ADMIN` não significa acesso invisível a todos os tenants da plataforma.

`SUPER_ADMIN` é reservado à administração excepcional da plataforma. Seu uso deve ser limitado, auditado e, em produção, tratado como elevação consciente ou mecanismo de emergência. As rotas comuns não usam esse papel como atalho.

### Persistência

- Repositórios e serviços recebem o `ActorContext` obrigatoriamente.
- Consultas por identificador usam também `organization_id`; não existe `get_by_id` multiempresa sem escopo.
- Unicidade local ao tenant usa índices compostos, por exemplo `(organization_id, slug)`.
- Relações críticas usam constraints que impeçam ou detectem referência entre organizações, sempre que o PostgreSQL permitir de forma prática.
- Transferir um recurso para outra organização não é update comum; exige processo administrativo específico, auditoria e validação de todas as relações.
- Exclusão lógica preserva tenant e rastreabilidade.

### Autorização

Papéis definem ações dentro do escopo já autorizado. A ordem é:

1. autenticar;
2. resolver membership e tenant;
3. localizar o recurso dentro do tenant;
4. verificar papel e escopo de empresa;
5. executar e auditar.

Responder `404` em buscas de recurso fora do tenant reduz enumeração quando apropriado; `403` é usado quando a existência já é conhecida e a política requer clareza. A escolha deve ser consistente e testada.

### Jobs, providers, arquivos e cache

- Jobs persistem `organization_id`, mas o worker revalida o recurso ao executar.
- Provider recebe somente contexto mínimo da organização que solicitou a tarefa.
- Chaves de armazenamento incluem prefixo opaco do tenant; download passa por autorização ou URL assinada curta.
- Cache inclui organização e, quando necessário, empresa e usuário na chave.
- Notificações validam tenant e destinatário.
- Audit log registra tenant e ator, sem permitir leitura cruzada.

### Defesa em profundidade

Na fundação, o controle principal fica na aplicação, acompanhado de constraints e testes de banco. PostgreSQL Row-Level Security pode ser adicionado depois como segunda barreira, após definir corretamente conexões de worker, migrations e administração. A ausência inicial de RLS não autoriza consultas sem escopo.

## Regras de implementação

- Falhar cedo quando uma operação multiempresa não recebe `ActorContext`.
- Não aceitar `organization_id` em DTO público de criação quando ele puder ser derivado da sessão.
- Não expor listagem global em serviços usados por usuários comuns.
- Não reutilizar objetos de ORM entre contextos de tenant.
- Não incluir dados de tenant em memória, prompt ou fixture de outro tenant.
- Toda nova tabela deve declarar se é global ou multiempresa; a escolha entra na revisão.
- Alteração de membership ou papel gera audit log.

## Testes obrigatórios

Para cada recurso multiempresa:

1. usuário autorizado acessa o próprio recurso;
2. usuário da organização A não lê o identificador da organização B;
3. usuário da A não altera, exclui, comenta, aprova ou baixa arquivo da B;
4. filtros, paginação, busca e contadores não revelam a existência de B;
5. job da A não processa recurso da B mesmo com payload manipulado;
6. cache e URL assinada não atravessam tenant;
7. `VIEWER` não escreve e cliente fica no escopo da empresa;
8. `SUPER_ADMIN`, quando testado, gera evidência de auditoria.

## Consequências

### Positivas

- O isolamento passa a ser requisito explícito de todas as camadas.
- Usuários podem participar de mais de uma organização sem duplicar conta.
- A equipe da agência acessa somente os clientes concedidos.
- Testes e índices compostos tornam regressões mais visíveis.

### Custos e cuidados

- Toda consulta e job carrega contexto adicional.
- Índices e chaves únicas precisam incluir o tenant.
- Operações administrativas globais exigem caminho separado e maior controle.
- RLS futuro demandará planejamento de conexão e política, não apenas habilitar uma opção.

## Alternativas consideradas

### Um banco por cliente

Oferece isolamento físico mais forte, mas aumenta provisionamento, migrations, custo e operação para a escala inicial. Pode ser reavaliado para requisitos contratuais específicos.

### Um schema por cliente

Reduz parte do risco de consulta cruzada, mas complica migrations, pooling e observabilidade. Não foi escolhido para a versão 1.0.

### Filtro apenas no frontend

Rejeitado: qualquer chamada direta à API contornaria a proteção.

### Acesso global implícito para toda a agência

Rejeitado: amplia o impacto de uma conta comprometida e dificulta comprovar menor privilégio.

## Critérios de aceite

1. **ADR2-01:** toda tabela classificada como multiempresa possui `organization_id` obrigatório.
2. **ADR2-02:** serviços e repositórios multiempresa exigem contexto autenticado.
3. **ADR2-03:** duas organizações em fixtures demonstram negação cruzada em API, jobs e arquivos.
4. **ADR2-04:** cliente fica limitado à empresa concedida e ao próprio tenant.
5. **ADR2-05:** acesso da agência decorre de membership explícita.
6. **ADR2-06:** mudança de papel, membership e uso administrativo excepcional são auditados.
7. **ADR2-07:** criação não confia em `organization_id` arbitrário do frontend.
8. **ADR2-08:** a revisão de nova entidade decide e testa seu escopo de tenant.
