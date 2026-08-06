# QA Report — Fase IA v1

Data: 2026-08-06

QA Lead: Codex

Branch: `agent/camada-ia-v1`

Commits corretivos auditados: `99552a7`, `ea42bd7`, `423aa33`, `8c2418d`, `8aa3e9c`

PR: #4, aberto e em Draft

## Conclusão executiva

QA-004 e QA-005 foram corrigidos. Dados de IA agora participam de exportação, anonimização, retenção e auditoria LGPD, e custos informados pelo OpenRouter são persistidos sem transformar ausência em zero. Migrações, validação local completa e a CI do run 31094333781 passaram. O PR permanece em Draft porque QA-006 continua alto.

Recomendação: **NO-GO para merge**. O piloto ainda depende de tratar ou aceitar formalmente QA-006.

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
| Migração | `0016_ai_costs (head)` |
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
| Backend | PASS: 234, 1 warning de depreciação Starlette/httpx |
| Worker | PASS: 41 |
| Frontend | PASS: 54 em 20 arquivos |
| E2E offline | PASS: 10, incluindo IA mock e acessibilidade |
| npm audit frontend/E2E | PASS: 0 vulnerabilidades |
| pip-audit | backend sem vulnerabilidades conhecidas; worker acusou seis advisories no pip 25.0.1 da imagem; dependências locais do projeto foram ignoradas por não existirem no PyPI |
| Backup + verificação + restauração | PASS |
| Migrações base/0008/0014 até 0016, downgrade e reupgrade | PASS; cinco tabelas `ai_*` íntegras |
| `alembic check` | PASS em todos os caminhos validados |
| CI PR #4 | PASS no run 31094333781: backend/worker, frontend, Compose/contratos e fluxo vertical E2E; PR continua Draft |

Contagem da rodada automatizada: 234 backend + 41 worker + 54 frontend + 10 E2E = **339 aprovados**. Não houve falha de teste.

## Cobertura funcional

Foram exercitados por testes existentes: autenticação, convite e recuperação, papéis oficiais, isolamento multiempresa, onboarding, catálogos, mídia privada, estratégia/calendário, conteúdo/versionamento/comparação, aprovações, conteúdo sensível, notificações, providers, LGPD pré-IA, relatórios, backup/restauração, acessibilidade essencial e viewports móveis.

Foram comprovados manualmente pela API e pelo proxy do frontend: autenticação OpenRouter, structured JSON, três alternativas persistidas, provider/modelo real, tokens, ausência de publicação automática, histórico no frontend e fallback OpenRouter → Hermes indisponível → Mock simulado.

Permanecem sem evidência completa: todas as 12 tarefas em combinações 1/3, cancelamento, concorrência e idempotência de requisição, aplicação de alternativa, limite diário/429 real, leitor de tela, outros navegadores e falhas destrutivas de backup.

## Cinco problemas prioritários

1. QA-006 — cancelamento, aplicação de alternativa e idempotência não têm contrato completo.
2. QA-007 — Hermes configurado ainda não equivale a saudável.
3. QA-008 — CSP ainda permite `unsafe-inline`.
4. QA-009 — lista de conteúdos é o endpoint mais pesado medido.
5. QA-010 — auditoria Python local e pip antigo na imagem worker.

Detalhes reproduzíveis estão em `BUGS.md`.

## Decisão

- PR #4 pode sair de Draft? **Não**.
- Pode ser mesclado? **Não**.
- Pronto para piloto? **Ainda não**; QA-001 a QA-005 estão resolvidos/mitigados, mas QA-006 precisa de resolução ou aceite formal.
- Pronto para dados reais? **Condicionalmente não** até o gate acima e o aceite dos riscos restantes.
