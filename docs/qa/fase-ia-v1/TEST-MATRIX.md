# Matriz de testes — Fase IA v1

Legenda: PASS, FAIL, PARCIAL, NÃO EXECUTADO.

| Área | Estado | Evidência/limite |
|---|---|---|
| Ambiente, branch, remote, URLs | PASS | inventário em `QA-REPORT.md` |
| Stack e healthchecks | PASS | seis serviços saudáveis |
| Migração atual | PASS | 0017 head |
| Base→0017, 0008→0017 e 0016→0017 | PASS | bancos temporários isolados |
| Downgrade base e reupgrade | PASS | dois bancos temporários |
| Alembic drift | PASS | nove constraints alinhadas; base/0008/0013/0014 e `alembic check`; QA-001 resolvido |
| Lint, tipos e build | PASS | `make lint` |
| Backend | PASS | 240/240; ambiente de teste força providers offline |
| Worker | PASS | 41/41 |
| Frontend unitário | PASS | 52/52 |
| E2E | PASS | 10/10 offline por configuração dedicada |
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
| LGPD sobre IA | PASS | exportação 1.1, anonimização, retenção, auditoria e tenant; QA-004 resolvido |
| OpenRouter autenticação | PASS | HTTP 200, chave não exibida |
| OpenRouter structured output | PASS | JSON válido e três alternativas persistidas |
| OpenRouter tokens/modelo | PASS | modelo real e usage persistidos |
| OpenRouter custo | PASS | Decimal, confirmado/estimado/desconhecido, tentativa/uso/exportação/relatório/UI; QA-005 resolvido |
| OpenRouter 401/timeout/invalid schema | PARCIAL | falsos/unitários e fallback; 429 real não provocado para evitar abuso |
| 12 tarefas de IA × 1/3 alternativas | PARCIAL | enum/UI existem; não há matriz funcional completa por tarefa |
| Regeneração e feedback | PARCIAL | contratos presentes; cobertura limitada |
| Aplicar alternativa/cancelar/idempotência | PASS | tenant, papéis, inexistentes, concorrência, replay, audit e E2E offline; QA-006 resolvido |
| Hermes/Ollama | PARCIAL | indisponibilidade e fallback confirmados; instalação proibida; health/model fake incompletos |
| Mock offline | PASS | APP_ENV/pytest/Makefile/Compose/provider bloqueiam rede externa; QA-002 resolvido |
| Provider/modelo/fallback/selo no frontend | PASS | proxy/histórico e componentes |
| Backup PostgreSQL/MinIO/checksum | PASS | backup e verify |
| Restore isolado | PASS | banco e objetos restaurados e descartados |
| Backup corrompido/ausente | PARCIAL | scripts validam; não corrompido deliberadamente nesta rodada |
| npm audit | FAIL | uma alta em `js-yaml`; QA-012 aberto |
| pip-audit | PARCIAL | backend sem vulnerabilidade conhecida; imagem worker acusou seis advisories do pip 25.0.1, ferramenta de build não exposta; CI atualiza pip antes da auditoria |
| Segredos Git/logs | PASS | zero padrões; `.env` ignorado |
| Permissão do `.env` | PASS | `.env` fuseblk permanece 777, mas está sem segredo; chave local em arquivo Linux 600 e doctor impede uso inseguro; QA-003 mitigado |
| Headers/CSP | PARCIAL | headers defensivos presentes; unsafe-inline; QA-008 |
| Performance | PARCIAL | sete endpoints e memória; IA/aprovação/LGPD não medidos em série |
| Instalação limpa e falhas de recursos | PARCIAL | doctor/setup existentes; máquina limpa externa/CAV1 não repetida |
| Git/PR/CI | FAIL | head funcional no run 31129195136: backend/worker e Compose passaram; frontend bloqueado pelo audit QA-012; E2E local passou; PR Draft preservado |

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
