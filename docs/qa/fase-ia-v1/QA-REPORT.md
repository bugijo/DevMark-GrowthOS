# QA Report — Fase IA v1

Data: 2026-08-05

QA Lead: Codex

Branch: `agent/camada-ia-v1`

Commits corretivos auditados: `99552a7`, `ea42bd7`, `423aa33`

PR: #4, aberto e em Draft

## Conclusão executiva

O sistema está executável localmente e os três bloqueadores solicitados foram corrigidos: o metadata não apresenta drift, as suítes não podem construir/chamar providers externos e a chave local não fica mais no `.env` do filesystem fuseblk. A validação local completa passou. O PR permanece em Draft porque QA-004 e QA-005 continuam altos e a CI do GitHub ainda deve validar os novos commits.

Recomendação: **NO-GO para merge e para dados reais**. Piloto apenas depois dos bloqueios e achados altos serem corrigidos e revalidados.

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
| Migração | `0014_ai_generations (head)` |
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
| Backend | PASS: 220, 1 warning de depreciação Starlette/httpx |
| Worker | PASS: 41 |
| Frontend | PASS: 52 em 19 arquivos |
| E2E offline | PASS: 10, incluindo IA mock e acessibilidade |
| npm audit frontend/E2E | PASS: 0 vulnerabilidades |
| pip-audit | backend sem vulnerabilidades conhecidas; worker acusou seis advisories no pip 25.0.1 da imagem; dependências locais do projeto foram ignoradas por não existirem no PyPI |
| Backup + verificação + restauração | PASS |
| Migrações base/0008/0013/0014, downgrade e reupgrade | PASS em bancos isolados |
| `alembic check` | PASS em todos os caminhos validados |
| CI PR #4 | PENDENTE de nova execução após push; PR continua Draft |

Contagem da rodada automatizada: 220 backend + 41 worker + 52 frontend + 10 E2E = **323 aprovados**. Não houve falha de teste. Validações operacionais e de migração são registradas separadamente na matriz.

## Cobertura funcional

Foram exercitados por testes existentes: autenticação, convite e recuperação, papéis oficiais, isolamento multiempresa, onboarding, catálogos, mídia privada, estratégia/calendário, conteúdo/versionamento/comparação, aprovações, conteúdo sensível, notificações, providers, LGPD pré-IA, relatórios, backup/restauração, acessibilidade essencial e viewports móveis.

Foram comprovados manualmente pela API e pelo proxy do frontend: autenticação OpenRouter, structured JSON, três alternativas persistidas, provider/modelo real, tokens, ausência de publicação automática, histórico no frontend e fallback OpenRouter → Hermes indisponível → Mock simulado.

Permanecem sem evidência completa: todas as 12 tarefas em combinações 1/3, cancelamento, concorrência e idempotência de IA, aplicação de alternativa a conteúdo, limite diário em ambiente real, 429 real, LGPD incluindo snapshots de IA, leitor de tela real, navegadores além de Chromium e falhas destrutivas de backup. Esses itens constam como PARCIAL ou NÃO EXECUTADO na matriz.

## Cinco problemas prioritários

1. QA-004 — exportação/anonimização LGPD não contempla gerações e snapshots de IA.
2. QA-005 — custo retornado pelo OpenRouter não é persistido/exibido pela aplicação.
3. QA-006 — cancelamento, aplicação de alternativa e idempotência não têm contrato completo.
4. QA-007 — Hermes configurado ainda não equivale a saudável.
5. QA-008 — CSP ainda permite `unsafe-inline`.

Detalhes reproduzíveis estão em `BUGS.md`.

## Decisão

- PR #4 pode sair de Draft? **Não**.
- Pode ser mesclado? **Não**.
- Pronto para piloto? **Ainda não**; QA-001/002/003 estão corrigidos, mas QA-004/005 precisam ser resolvidos ou formalmente aceitos, e a CI deve ficar verde.
- Pronto para dados reais? **Não**.
