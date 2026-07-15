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
make setup
```

`make setup` usa apenas GNU Make, Docker e Docker Compose. Ele prepara `.env`, constrói a stack, aplica migrações, carrega dados fictícios e aguarda os healthchecks. Nunca é necessário inserir uma chave paga.

Para desenvolver e executar os gates unitários no host:

```bash
make install
```

Esse comando requer Python 3.12 com `venv` — normalmente `python3.12-venv` em Debian/Ubuntu — além de Node.js 22 e npm. `make e2e` é Docker-only e não depende dessa instalação local.

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

Depois de `make install`, execute:

```bash
make lint
make test
```

Para validar o fluxo vertical real em contêineres:

```bash
make e2e
```

As imagens de produção do backend e frontend são enxutas e não carregam pytest, Ruff, mypy, ESLint ou Vitest. Por isso, não tente executar essas ferramentas com `docker compose exec` dentro das imagens. Os alvos do Makefile reproduzem o fluxo correto usado pela CI.

Uma mudança não está pronta quando um teste foi ignorado por falta de configuração. Corrija o ambiente ou registre claramente o bloqueio. A suíte usa provider mock e não acessa API paga.

Linha de base verificada no primeiro ciclo: 28 testes de backend, 7 de worker, 15 de frontend e 3 cenários E2E. Novas mudanças não podem reduzir silenciosamente essa cobertura funcional.

## Banco e migrações

- Toda mudança de schema inclui migração Alembic e teste correspondente.
- Não edite migração já compartilhada; crie uma nova.
- Seeds são idempotentes e contêm somente dados fictícios.
- Evite operações destrutivas; quando inevitáveis, documente backup, impacto e recuperação.
- Verifique índices e vínculo à organização em toda nova entidade multiempresa.
- Use `make migrate` e `make seed` contra a stack local; nunca execute o seed demo em produção.

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
- [ ] `make e2e` passa quando o fluxo vertical foi afetado.
- [ ] Nenhum segredo ou dado real foi incluído.
- [ ] Documentação e changelog foram atualizados.
- [ ] Estados vazios, erros e mobile foram considerados.

## Segurança

Não abra issue pública com senha, token, dado pessoal, vulnerabilidade explorável ou informação de cliente. Interrompa a publicação do material, informe o responsável pelo repositório por canal privado e providencie rotação quando houver exposição de credencial.

Não tente criar criptografia própria. Use bibliotecas mantidas, escopos mínimos e dados fictícios nos testes.
