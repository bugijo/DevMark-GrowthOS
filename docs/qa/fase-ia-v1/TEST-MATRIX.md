# Matriz de testes — Fase IA v1

Legenda: PASS, FAIL, PARCIAL, NÃO EXECUTADO.

| Área | Estado | Evidência/limite |
|---|---|---|
| Ambiente, branch, remote, URLs | PASS | inventário em `QA-REPORT.md` |
| Stack e healthchecks | PASS | seis serviços saudáveis |
| Migração atual | PASS | 0014 head |
| Base→0014 e 0008→0014 | PASS | bancos temporários isolados |
| Downgrade base e reupgrade | PASS | dois bancos temporários |
| Alembic drift | FAIL | nove constraints; QA-001 |
| Lint, tipos e build | PASS | `make lint` |
| Backend | FAIL | 213/214 com env local; 214/214 com externo desligado |
| Worker | PASS | 41/41 |
| Frontend unitário | PASS | 52/52 |
| E2E | FAIL | 9/10 com env local; 10/10 offline explícito |
| Acessibilidade automatizada | PASS | agência/cliente, axe WCAG 2.1 AA |
| Viewport 360 px | PASS | login, operação e equipe |
| Viewports 768/1280 | PARCIAL | layout exercitado, sem matriz visual completa |
| Leitor de tela | NÃO EXECUTADO | ferramenta/operador humano não disponível |
| Autenticação/sessão/CSRF/rate limit | PASS | testes backend/E2E existentes |
| Convite e recuperação | PASS | API, Mailpit e uso único |
| Papéis oficiais | PASS | matriz de permissões automatizada |
| “Gestor” e “profissional habilitado” | PARCIAL | gestor mapeia AGENCY_ADMIN; profissional é grant, não papel distinto |
| Isolamento organização/cliente/IDOR | PASS | testes negativos existentes |
| Onboarding de 15 etapas | PARCIAL | fluxo, persistência, validações e mobile cobertos; concorrência e matriz completa de uploads não repetidas manualmente |
| Brand Kit, catálogos e mídia | PASS | API, MIME/tamanho, scanner, URLs e tenant tests |
| Estratégia, calendário e comparação | PASS | backend, frontend e E2E fase 2/3 |
| Conteúdo e aprovações | PASS | versionamento, texto/imagem, alteração e publicação manual |
| Conteúdo sensível | PASS | classificador, bloqueio e revisão profissional automatizados |
| Notificações e resumos | PASS | backend/worker/E2E/Mailpit |
| LGPD pré-IA | PASS | consentimento, exportação, requests, anonimização |
| LGPD sobre IA | FAIL | snapshots/instruções não tratados; QA-004 |
| OpenRouter autenticação | PASS | HTTP 200, chave não exibida |
| OpenRouter structured output | PASS | JSON válido e três alternativas persistidas |
| OpenRouter tokens/modelo | PASS | modelo real e usage persistidos |
| OpenRouter custo | FAIL | custo oficial não mapeado; QA-005 |
| OpenRouter 401/timeout/invalid schema | PARCIAL | falsos/unitários e fallback; 429 real não provocado para evitar abuso |
| 12 tarefas de IA × 1/3 alternativas | PARCIAL | enum/UI existem; não há matriz funcional completa por tarefa |
| Regeneração e feedback | PARCIAL | contratos presentes; cobertura limitada |
| Aplicar alternativa/cancelar/idempotência | FAIL | contratos não encontrados; QA-006 |
| Hermes/Ollama | PARCIAL | indisponibilidade e fallback confirmados; instalação proibida; health/model fake incompletos |
| Mock offline | FAIL | funciona quando externo desligado, mas suíte não isola env; QA-002 |
| Provider/modelo/fallback/selo no frontend | PASS | proxy/histórico e componentes |
| Backup PostgreSQL/MinIO/checksum | PASS | backup e verify |
| Restore isolado | PASS | banco e objetos restaurados e descartados |
| Backup corrompido/ausente | PARCIAL | scripts validam; não corrompido deliberadamente nesta rodada |
| npm audit | PASS | zero vulnerabilidades frontend/E2E |
| pip-audit | PARCIAL | CI passou; venv isolado local bloqueado por ensurepip ausente |
| Segredos Git/logs | PASS | zero padrões; `.env` ignorado |
| Permissão do `.env` | FAIL | modo 777; QA-003 |
| Headers/CSP | PARCIAL | headers defensivos presentes; unsafe-inline; QA-008 |
| Performance | PARCIAL | sete endpoints e memória; IA/aprovação/LGPD não medidos em série |
| Instalação limpa e falhas de recursos | PARCIAL | doctor/setup existentes; máquina limpa externa/CAV1 não repetida |
| Git/PR/CI | FAIL | pasta Git duplicada não rastreada; CI vermelha; PR Draft preservado |

## Perfis

| Perfil solicitado | Mapeamento/evidência | Estado |
|---|---|---|
| Administrador da agência | AGENCY_ADMIN | PASS |
| Gestor | AGENCY_ADMIN; não há papel separado | PARCIAL |
| Estrategista | STRATEGIST | PASS |
| Criador de conteúdo | CONTENT_EDITOR | PASS |
| Designer | DESIGNER | PASS |
| Revisor | CLIENT_REVIEWER | PASS |
| Profissional habilitado | grant de revisão profissional | PASS automatizado, PARCIAL UX |
| Cliente/aprovador | CLIENT_OWNER/CLIENT_REVIEWER | PASS |
| Sem permissão | VIEWER | PASS |
| Outra organização | fixtures multi-tenant | PASS |
