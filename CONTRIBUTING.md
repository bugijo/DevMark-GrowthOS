# Como contribuir

Obrigado por contribuir com o DevMark GrowthOS. O objetivo é construir uma versão 1.0 simples, segura e testável, sem misturar este produto com o site institucional da DevMark IA.

Leia antes de começar:

- [README.md](README.md), para visão e execução;
- [AGENTS.md](AGENTS.md), para regras técnicas e de segurança;
- `docs/01-escopo-versao-1.md`, para o limite da versão;
- [backlog](docs/backlog/versao-1.md) e [milestones](docs/milestones/versao-1.md), para dependências e critérios de aceite.

## Preparar o ambiente

Use Docker Compose como caminho principal:

```bash
cp .env.example .env
docker compose config
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

O modo local deve usar providers mock. Nunca é necessário inserir uma chave paga para desenvolver ou executar testes.

## Escolher e implementar uma mudança

1. Escolha um item com ID no backlog e confirme que suas dependências foram concluídas.
2. Crie uma branch curta a partir da base atual, como `feat/V1-APR-002-decisao-cliente`.
3. Antes de editar, verifique `git status` e preserve mudanças que não sejam suas.
4. Implemente o menor incremento completo: domínio, autorização, persistência, API, interface e teste, conforme o item exigir.
5. Valide isolamento entre organizações e papéis no backend.
6. Atualize documentação, contrato OpenAPI e changelog quando houver mudança observável.
7. Faça commits pequenos e abra um pull request com evidências de teste.

Não altere o repositório `bugijo/DevMark-ia`. Não ative publicação social, anúncios reais, gasto automático ou WhatsApp oficial na versão 1.0.

## Padrão de commits

Use mensagens curtas no imperativo:

```text
feat(content): cria versão com provider mock
fix(auth): impede acesso entre organizações
test(approvals): cobre pedido de alteração
docs(architecture): registra decisão de jobs
```

Tipos aceitos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci` e `security`. O escopo é recomendado. Um commit deve representar uma intenção e permanecer revisável.

## Qualidade mínima

Execute os comandos aplicáveis antes de enviar:

```bash
docker compose config
docker compose exec backend pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run test
docker compose run --rm e2e
```

Uma mudança não está pronta quando o teste foi ignorado por falta de configuração. Corrija o ambiente ou registre claramente o bloqueio. A suíte padrão não acessa rede externa nem API paga.

## Banco e migrações

- Toda mudança de schema inclui migração Alembic e teste correspondente.
- Não edite migração já compartilhada; crie uma nova.
- Seeds são idempotentes e contêm somente dados fictícios.
- Evite operações destrutivas; quando inevitáveis, documente backup, impacto e recuperação.
- Verifique índices e vínculo à organização em toda nova entidade multiempresa.

## Testes esperados

- unidade para regras de domínio e transições;
- integração para banco, API, autenticação e worker;
- contrato para providers;
- ponta a ponta para jornadas críticas;
- caso negativo entre duas organizações diferentes;
- caso negativo para papel sem permissão;
- regressão para todo bug corrigido;
- acessibilidade e viewport móvel em interfaces do cliente.

## Pull request

Inclua:

- ID e objetivo do backlog;
- resumo em linguagem simples;
- comportamento que funciona e limitações conhecidas;
- como testar e resultado dos comandos executados;
- migrações e impacto em dados;
- análise de autorização, multiempresa, privacidade e audit log;
- screenshots ou vídeo curto quando houver interface;
- riscos, rollback e próximos passos.

Checklist:

- [ ] Escopo da versão 1.0 respeitado.
- [ ] Provider mock continua sendo suficiente.
- [ ] Isolamento por organização testado no backend.
- [ ] Papéis e transições validados.
- [ ] Audit log criado quando necessário.
- [ ] Lint, tipos e testes passam.
- [ ] Nenhum segredo ou dado real foi incluído.
- [ ] Documentação e changelog foram atualizados.
- [ ] Estados vazios, erros e mobile foram considerados.

## Segurança

Não abra issue pública com senha, token, dado pessoal, vulnerabilidade explorável ou informação de cliente. Interrompa a publicação do material, informe o responsável pelo repositório por canal privado e providencie rotação quando houver exposição de credencial.

Não tente criar criptografia própria. Use bibliotecas mantidas, escopos mínimos e dados fictícios nos testes.
