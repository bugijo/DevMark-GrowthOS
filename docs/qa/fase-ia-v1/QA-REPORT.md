# QA Report — Fase IA v1

Data: 2026-08-05

QA Lead: Codex

Branch: `agent/camada-ia-v1`

Commit auditado: `66528c2dcbb9d24f88d8b3ae54c0b52857fec6c3`

PR: #4, aberto e em Draft

## Conclusão executiva

O sistema está executável localmente e os fluxos consolidados das fases anteriores têm boa cobertura. A camada de IA funciona com OpenRouter real, persiste alternativas e identifica provider/modelo/fallback. Entretanto, o PR não pode sair de Draft: a CI está vermelha por drift de nove constraints, as suítes offline podem chamar o OpenRouter real quando o `.env` local contém chave e o arquivo `.env` está com permissão `777` neste host.

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
| `make doctor` | PASS com 36 OK e 1 aviso: `.env` modo 777 |
| `make validate` | PASS |
| `make lint` | PASS: Ruff, formatação, mypy, ESLint, TypeScript e build |
| Backend com ambiente local | FAIL: 213 passaram, 1 falhou; teste offline chamou OpenRouter |
| Backend com `AI_EXTERNAL_ENABLED=false` | PASS: 214, 1 warning de depreciação Starlette/httpx |
| Worker | PASS: 41 |
| Frontend | PASS: 52 em 19 arquivos |
| E2E com ambiente local | FAIL: 9 passaram, 1 falhou; cenário offline recebeu OpenRouter |
| E2E com IA externa desligada no comando | PASS: 10 |
| npm audit frontend/E2E | PASS: 0 vulnerabilidades |
| pip-audit | CI anterior passou; repetição isolada local bloqueada por ausência de `python3.12-venv` |
| Backup + verificação + restauração | PASS |
| Migrações base/0008 até 0014, downgrade e reupgrade | PASS, exceto drift |
| `alembic check` | FAIL: nove constraints fora do metadata |
| CI PR #4 | FAIL: Backend/worker; E2E pulado |

Contagem da rodada automatizada, considerando cada caso executado uma vez na configuração apropriada: 214 backend + 41 worker + 52 frontend + 10 E2E = **317 aprovados**. As execuções na configuração local produziram **2 falhas de configuração** (uma backend e uma E2E) que representam o mesmo defeito. Validações operacionais e de migração são registradas separadamente na matriz.

## Cobertura funcional

Foram exercitados por testes existentes: autenticação, convite e recuperação, papéis oficiais, isolamento multiempresa, onboarding, catálogos, mídia privada, estratégia/calendário, conteúdo/versionamento/comparação, aprovações, conteúdo sensível, notificações, providers, LGPD pré-IA, relatórios, backup/restauração, acessibilidade essencial e viewports móveis.

Foram comprovados manualmente pela API e pelo proxy do frontend: autenticação OpenRouter, structured JSON, três alternativas persistidas, provider/modelo real, tokens, ausência de publicação automática, histórico no frontend e fallback OpenRouter → Hermes indisponível → Mock simulado.

Permanecem sem evidência completa: todas as 12 tarefas em combinações 1/3, cancelamento, concorrência e idempotência de IA, aplicação de alternativa a conteúdo, limite diário em ambiente real, 429 real, LGPD incluindo snapshots de IA, leitor de tela real, navegadores além de Chromium e falhas destrutivas de backup. Esses itens constam como PARCIAL ou NÃO EXECUTADO na matriz.

## Cinco problemas prioritários

1. QA-001 — CI bloqueada pelo drift das nove constraints.
2. QA-002 — testes declarados offline usam OpenRouter real quando a chave local existe.
3. QA-003 — `.env` com chave está legível/escrevível por grupo e outros (`777`).
4. QA-004 — exportação/anonimização LGPD não contempla gerações e snapshots de IA.
5. QA-005 — custo retornado pelo OpenRouter não é persistido/exibido pela aplicação.

Detalhes reproduzíveis estão em `BUGS.md`.

## Decisão

- PR #4 pode sair de Draft? **Não**.
- Pode ser mesclado? **Não**.
- Pronto para piloto? **Não na configuração atual**; condicional após corrigir QA-001, QA-002 e QA-003 e revalidar QA-004/005.
- Pronto para dados reais? **Não**.
