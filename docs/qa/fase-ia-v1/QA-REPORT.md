# QA Report — Fase IA v1

Data: 2026-08-07

QA Lead: Codex

Branch: `agent/camada-ia-v1`

Commits corretivos auditados: `99552a7`, `ea42bd7`, `423aa33`, `8c2418d`, `8aa3e9c`, `cb48c6c`, `cd7fc31`

PR: #4, aberto e em Draft

## Conclusão executiva

A rodada final reavaliou QA-007 a QA-011, executou inspeção visual em 360/768/1280, teclado, segurança manual, desempenho, regressão completa, auditorias e OpenRouter real. Não existe bloqueador, crítico ou alto aberto. Nenhum dos achados restantes exige correção para um piloto interno com dados fictícios.

Recomendação formal: **GO FOR CONTROLLED PILOT**, mantendo o PR em Draft até autorização explícita. A decisão não libera dados reais, produção, merge nem conclusão da versão 1.0; CAV1-23 continua bloqueado.

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
| pip-audit | seis advisories no instalador `pip 25.0.1`; nenhuma dependência funcional conhecida afetada; correção obrigatória antes de dados reais |
| Backup + verificação + restauração | PASS |
| Migrações base/0008/0016 até 0017, downgrade e reupgrade | PASS; dados anteriores compatíveis |
| `alembic check` | PASS em todos os caminhos validados |
| CI do head auditado `4f3aee3` | PASS no run 31150092463: Compose/contratos, backend/worker, frontend com audit/build e E2E vertical |
| Segurança manual | PASS condicionado: CSRF sem token 403, provider negado ao cliente 403, MinIO privado 403, cookies HttpOnly/SameSite=Lax, headers presentes; CSP ainda usa unsafe-inline |
| Desempenho | PASS condicionado: conteúdos p95 máximo 719,3 ms para orçamento de 750 ms; demais endpoints medidos abaixo |
| OpenRouter real | PASS: 26,9 s, `google/gemma-4-26b-a4b-it:free`, sem fallback/mock, aprovação obrigatória |

Contagem da rodada automatizada: 240 backend + 41 worker + 54 frontend + 10 E2E = **345 aprovados**. Não houve falha de teste.

## Cobertura funcional

Foram exercitados por testes existentes: autenticação, convite e recuperação, papéis oficiais, isolamento multiempresa, onboarding, catálogos, mídia privada, estratégia/calendário, conteúdo/versionamento/comparação, aprovações, conteúdo sensível, notificações, providers, LGPD pré-IA, relatórios, backup/restauração, acessibilidade essencial e viewports móveis.

Foram comprovados manualmente pela API e pelo proxy do frontend: autenticação OpenRouter, structured JSON, três alternativas persistidas, provider/modelo real, tokens, ausência de publicação automática, histórico no frontend e fallback OpenRouter → Hermes indisponível → Mock simulado.

Permanecem sem evidência completa: todas as 12 tarefas em combinações 1/3, interrupção de chamada HTTP síncrona já iniciada, limite diário/429 real, sessão humana com leitor de tela, outros navegadores, falhas destrutivas de backup e instalação realmente independente CAV1-23.

## Cinco problemas prioritários

1. QA-007 — Hermes configurado ainda não equivale a saudável.
2. QA-008 — CSP ainda permite `unsafe-inline`.
3. QA-009 — lista de conteúdos é o endpoint mais pesado medido.
4. QA-010 — auditoria Python local e pip antigo na imagem worker.
5. QA-011 — buildx ausente e actions v4 emitem avisos operacionais.

Detalhes reproduzíveis estão em `BUGS.md`.

## Decisão

- Piloto com dados fictícios? **Sim, controlado**.
- Piloto interno? **Sim**, na branch e com monitoramento.
- Dados reais? **Não**.
- Produção? **Não**.
- PR #4 pode sair de Draft? **Tecnicamente sim para revisão, mas somente após autorização explícita; permanece Draft nesta rodada**.
- Pode ser mesclado? **Não**, até CAV1-23, revisão humana e fechamento dos gates de dados reais.

## Condições do piloto

- somente dados fictícios, sem prontuário, dado clínico identificável, cliente real ou segredo no `.env` fuseblk;
- OpenRouter pode receber apenas contexto sanitizado de marca demo; Hermes deve ser tratado como indisponível; Mock precisa permanecer claramente simulado;
- monitorar latência/payload de conteúdos, fallback, rate limit, custo, erros 5xx, isolamento e logs;
- interromper imediatamente em vazamento/tenant crossing, segredo em log, publicação/aprovação automática, conteúdo sensível sem revisão, custo inesperado, p95 repetido acima de 750 ms ou fallback não identificado.

## Dependências e infraestrutura

| Item | Classificação | Justificativa |
|---|---|---|
| `pip 25.0.1` | MUST FIX BEFORE REAL DATA | seis advisories, sem caminho de execução pelo app no piloto |
| `actions/checkout@v4` / Node 20 | BACKLOG | runner força Node 24 e a CI passa; atualizar antes da remoção do suporte |
| Starlette/httpx | BACKLOG | aviso limitado ao adaptador de testes, sem falha funcional |
| Docker buildx | BACKLOG | builder padrão funciona; apenas ruído e desempenho de build |
| Hermes/Ollama ausente | ACCEPTABLE FOR CONTROLLED PILOT | opcional, OpenRouter prioritário e Mock obrigatório; bloquear dados reais até health confiável |
| CSP `unsafe-inline` | MUST FIX BEFORE REAL DATA | defesa em profundidade insuficiente para exposição pública, aceitável somente em ambiente interno fictício |
