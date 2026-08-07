# QA Report — Fase IA v1

Data: 2026-08-07

QA Lead: Codex

Branch: `agent/camada-ia-v1`

Commits corretivos auditados: `99552a7`, `ea42bd7`, `423aa33`, `8c2418d`, `8aa3e9c`, `cb48c6c`, `cd7fc31`

PR: #4, aberto e em Draft

## Conclusão executiva

QA-012 foi corrigido com a atualização transitiva mínima de `js-yaml` 4.3.0 para 4.3.1 no lockfile do frontend. As auditorias npm e a CI integral estão verdes, sem regressão em QA-001 a QA-006. O PR permanece em Draft porque a decisão formal de release continua NO-GO pelos gates manuais e riscos médios restantes.

Recomendação: **NO-GO para merge**. O bloqueio alto QA-012 foi removido, mas o piloto ainda depende de QA-007, QA-008, QA-009 e dos gates manuais registrados na recomendação de release.

## Ambiente

| Item | Evidência |
|---|---|
| SO | Linux Mint 22.3, kernel 6.17.0-40-generic x86_64 |
| Docker | 29.1.3 |
| Docker Compose | 2.40.3 |
| Memória | 15 GiB total, sem swap; 5,1 GiB disponíveis no inventário |
| Disco | 285 GiB, 174 GiB livres (40% usado) |
| Frontend | http://127.0.0.1:3000 |
| Backend | http://127.0.0.1:8000 |
| Mailpit | http://127.0.0.1:8025 |
| PostgreSQL | 127.0.0.1:5432 |
| MinIO | 127.0.0.1:9000 e console 9001 |
| Migração | `0017_ai_lifecycle (head)` |
| Providers | OpenRouter configurado; Hermes apontado para Ollama local indisponível; Mock obrigatório |
| Modelo configurado | `openrouter/free` |
| Modelo real observado | `nvidia/nemotron-3-super-120b-a12b:free`; diagnóstico também escolheu `openai/gpt-oss-20b:free` |

Nenhuma chave foi registrada neste relatório. A busca no Git, histórico e logs retornou zero padrões de chave.

## Execuções principais

| Validação | Resultado |
|---|---|
| `make doctor` | PASS: 36 OK, 2 avisos explícitos sobre `.env` fuseblk sem segredo, 0 erros |
| `make validate` | PASS |
| `make lint` | PASS: Ruff, formatação, mypy, ESLint, TypeScript e build |
| Backend | PASS: 240, 1 warning de depreciação Starlette/httpx |
| Worker | PASS: 41 |
| Frontend | PASS: 54 em 20 arquivos |
| E2E offline | PASS: 10, incluindo IA mock e acessibilidade |
| npm audit frontend/E2E | PASS: 0 vulnerabilidades altas ou críticas; QA-012 resolvido |
| pip-audit | backend sem vulnerabilidades conhecidas; worker acusou seis advisories no pip 25.0.1 da imagem; dependências locais do projeto foram ignoradas por não existirem no PyPI |
| Backup + verificação + restauração | PASS |
| Migrações base/0008/0016 até 0017, downgrade e reupgrade | PASS; dados anteriores compatíveis |
| `alembic check` | PASS em todos os caminhos validados |
| CI do commit `cd7fc31` | PASS no run 31149722340: Compose/contratos, backend/worker, frontend com audit/build e E2E vertical |

Contagem da rodada automatizada: 240 backend + 41 worker + 54 frontend + 10 E2E = **345 aprovados**. Não houve falha de teste.

## Cobertura funcional

Foram exercitados por testes existentes: autenticação, convite e recuperação, papéis oficiais, isolamento multiempresa, onboarding, catálogos, mídia privada, estratégia/calendário, conteúdo/versionamento/comparação, aprovações, conteúdo sensível, notificações, providers, LGPD pré-IA, relatórios, backup/restauração, acessibilidade essencial e viewports móveis.

Foram comprovados manualmente pela API e pelo proxy do frontend: autenticação OpenRouter, structured JSON, três alternativas persistidas, provider/modelo real, tokens, ausência de publicação automática, histórico no frontend e fallback OpenRouter → Hermes indisponível → Mock simulado.

Permanecem sem evidência completa: todas as 12 tarefas em combinações 1/3, interrupção de chamada HTTP síncrona já iniciada, limite diário/429 real, leitor de tela, outros navegadores e falhas destrutivas de backup.

## Cinco problemas prioritários

1. QA-007 — Hermes configurado ainda não equivale a saudável.
2. QA-008 — CSP ainda permite `unsafe-inline`.
3. QA-009 — lista de conteúdos é o endpoint mais pesado medido.
4. QA-010 — auditoria Python local e pip antigo na imagem worker.
5. QA-011 — buildx ausente e actions v4 emitem avisos operacionais.

Detalhes reproduzíveis estão em `BUGS.md`.

## Decisão

- PR #4 pode sair de Draft? **Não**.
- Pode ser mesclado? **Não**.
- Pronto para piloto? **Ainda não**; QA-001 a QA-006 e QA-012 estão resolvidos/mitigados, mas faltam os gates manuais e o tratamento/aceite dos riscos médios.
- Pronto para dados reais? **Condicionalmente não** até o gate acima e o aceite dos riscos restantes.
