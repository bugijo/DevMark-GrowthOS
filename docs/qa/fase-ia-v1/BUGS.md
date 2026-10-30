# Bugs — Fase IA v1

## QA-001 — Drift de nove constraints bloqueia CI

- Área/severidade: Banco e CI — **BLOQUEADOR**
- Estado: **RESOLVIDO** em `99552a7`.
- Ambiente/perfil: banco PostgreSQL limpo; operador/CI
- Pré-condição: aplicar migrations até `0014_ai_generations`.
- Reprodução: executar `alembic upgrade head` e `alembic check`.
- Esperado: nenhum upgrade pendente.
- Atual: exit 255; Alembic sugere remover nove checks de notificações e revisão profissional.
- Evidência: CI run 30973261873, job 92201933568; reprodução em bancos `growthos_qa_base` e `growthos_qa_0008`.
- Risco: CI vermelha e divergência entre schema executável e metadata ORM.
- Recomendação: declarar as nove constraints no metadata ou alinhar migrations por migration aditiva; não editar migrations compartilhadas.
- Regressão: base→head, 0008→head, `alembic check`, downgrade base e novo upgrade.
- Causa raiz: as migrations criavam os nove checks, mas o metadata SQLAlchemy não os declarava; o autogenerate interpretava o banco correto como drift.
- Correção: os mesmos checks foram declarados nos modelos de notificações, entregas, resumos e revisão profissional, com teste de metadata. Nenhuma migration histórica foi editada e nenhuma migration destrutiva foi criada.
- Evidência pós-correção: `base→0014`, `0014→base→0014`, `0008→0014`, `0013→0014`, `0014→0014` e `alembic check` passaram em bancos PostgreSQL isolados; resultado: `No new upgrade operations detected`.
- Risco residual: mudanças futuras no schema ainda precisam manter migration e metadata sincronizados; o teste de regressão cobre os nove checks atuais.

## QA-002 — Suítes offline chamam OpenRouter real

- Área/severidade: IA/testes/privacidade — **CRÍTICO**
- Estado: **RESOLVIDO** em `ea42bd7`.
- Ambiente/perfil: host com `.env`, chave válida e `AI_EXTERNAL_ENABLED=true`; QA/desenvolvedor
- Reprodução: `make test` ou `make e2e`.
- Esperado: providers falsos/Mock, sem internet e sem custo.
- Atual: backend retorna `provider=openrouter`; teste backend leva ~46 s e falha. E2E offline também recebe OpenRouter. Com `AI_EXTERNAL_ENABLED=false`, 214 backend e 10 E2E passam.
- Evidência: `test_ai_generation_uses_offline_mock_and_records_history` e `ai-offline.spec.ts`.
- Risco: envio involuntário de fixtures/contexto, consumo de cota e suíte não determinística.
- Recomendação: configuração de teste deve sobrescrever explicitamente IA externa e chave; providers devem ser injetados/falsificados nos testes.
- Regressão: executar suítes com uma chave canário e provar, por servidor falso/contador, zero chamadas externas.
- Causa raiz: pytest e E2E herdavam `.env`, chave e URLs do ambiente local, e a construção do provider não possuía uma barreira própria para ambiente de teste.
- Correção: isolamento em camadas por `APP_ENV=test`/`PYTEST_CURRENT_TEST`, Makefile, `.env.test.example`, Compose/E2E, bloqueio de socket no pytest e recusa de construir provider externo em testes sem transporte falso explicitamente autorizado.
- Evidência pós-correção: 22 testes direcionados passaram mesmo com chave canário e URL Hermes inválida; depois passaram `make test` (220 backend, 41 worker e 52 frontend) e `make e2e` (10/10), incluindo o cenário Growth Agent offline com Mock e sem publicação automática.
- Risco residual: subprocessos que ignorem totalmente a configuração da aplicação devem continuar sendo cobertos pela configuração de execução/CI; a suíte padrão não depende de internet.

## QA-003 — `.env` local com modo 777

- Área/severidade: Segredos — **CRÍTICO**
- Estado: **RESOLVIDO COM MITIGAÇÃO OPERACIONAL** em `423aa33`.
- Ambiente/perfil: host Linux local; qualquer usuário/processo do host
- Reprodução: `stat -c '%a' .env` ou `make doctor`.
- Esperado: `600`.
- Atual: `777`.
- Risco: leitura e alteração da chave OpenRouter e demais segredos locais por terceiros.
- Recomendação: aplicar `chmod 600 .env` e tornar o doctor impeditivo quando houver segredo e permissões amplas.
- Regressão: doctor deve falhar ou alertar em severidade alta para modos com grupo/outros.
- Causa raiz: o projeto está em filesystem `fuseblk`, no qual o modo Unix do `.env` aparece como 777 e `chmod 600` não oferece a garantia esperada.
- Correção: a chave foi removida do `.env` ignorado e transferida, sem exibição, para arquivo do usuário em filesystem Linux, proprietário correto e modo 600. A aplicação aceita arquivo de segredo validado ou variável de processo; fontes simultâneas são rejeitadas. O doctor diferencia ambiente, filesystem e presença real de segredo, falhando em staging/produção quando inseguro.
- Evidência pós-correção: `make doctor` retornou 36 OK, dois avisos explicativos e zero erros; `APP_ENV=production ./scripts/doctor.sh` rejeitou a configuração insegura; 25 testes direcionados e mypy passaram. Busca em arquivos rastreados, histórico e logs não encontrou chave.
- Risco residual: o `.env` continuará reportando 777 enquanto o repositório permanecer em `fuseblk`; ele não pode receber segredos. Reinícios locais devem injetar a chave a partir do arquivo seguro ou de secret manager.

## QA-004 — LGPD não cobre snapshots de IA

- Área/severidade: LGPD/IA — **ALTO**
- Estado: **RESOLVIDO** em `8c2418d` (formatação validada em `e2c3269`).
- Ambiente/perfil: organização com gerações; titular e administrador
- Reprodução: criar geração, solicitar exportação/anonimização e revisar `services/privacy.py`.
- Esperado: inventário, exportação, retenção e anonimização tratam instrução, feedback e `context_snapshot` conforme política.
- Atual: nenhuma referência a `AIGeneration`/snapshots no serviço e testes LGPD.
- Risco: exportação incompleta e retenção de contexto após solicitação administrativa.
- Recomendação: definir política legal e incluir entidades IA com preservação auditável mínima.
- Regressão: exportação e anonimização tenant-scoped com geração antes/depois.
- Causa raiz: o fluxo de privacidade não consultava IA; as FKs de solicitante/feedback eram obrigatórias com `RESTRICT`, e retenção possuía cadastro sem execução.
- Correção: exportação `1.1` inclui somente IA do titular no tenant; identificadores viram `NULL`; instrução, feedback, snapshot e resultados recebem marcador sem conteúdo; métricas e auditoria mínima são preservadas. A retenção oferece dry-run, legal hold, isolamento, idempotência e audit log.
- Evidências: migration `0015_ai_privacy`, inventário `docs/19-lgpd-dados-ia.md` e testes de exportação, tenant, papel, anonimização, métricas e retenção. Downgrade bloqueia se referências já foram anonimizadas para impedir reidentificação ou `NOT NULL` inválido.
- Testes: regressão total passou com 234 backend, 41 worker, 54 frontend e 10 E2E offline.
- Risco residual: o vínculo persistido de alternativa aplicada foi adicionado no QA-006; a política continua conservadora e não apaga automaticamente a geração consolidada, preservando proveniência enquanto minimiza snapshots.

## QA-005 — Custo do OpenRouter não é persistido

- Área/severidade: IA/controle de gasto — **ALTO**
- Estado: **RESOLVIDO** em `8aa3e9c` (formatação validada em `e2c3269`).
- Ambiente/perfil: geração OpenRouter real; administrador
- Reprodução: gerar conteúdo e comparar resposta oficial com `estimated_cost_usd`.
- Esperado: custo retornado é salvo/exibido; ausência fica explícita.
- Atual: diagnóstico oficial retornou custo 0, mas provider não lê `usage.cost` e a aplicação persiste `null`.
- Risco: telemetria de gasto incompleta e limite financeiro não auditável.
- Recomendação: mapear custo somente quando fornecido, sem inventar valor.
- Regressão: provider falso com custo 0 e custo positivo, além de ausência do campo.
- Causa raiz: o adaptador ignorava `usage.cost`, e o campo legado não distinguia ausência, zero confirmado, estimativa e valor inválido.
- Correção: Decimal/Numeric registra valor, USD, estado `CONFIRMED|ESTIMATED|UNKNOWN`, origem e contabilização em geração, tentativa, uso, exportação, relatório e UI. Ausência/nulo/inválido permanece desconhecido.
- Evidências: migration `0016_ai_costs`, fixture sanitizada e `docs/20-custos-providers-ia.md`; seis registros anteriores permaneceram `NULL/UNKNOWN`; base, 0008 e 0014 chegaram a 0016 sem drift.
- Testes: positivo, zero, ausente, nulo, inválido, estimado, retry, fallback, regeneração, agregação, exportação, relatório, UI e provider fake passaram offline.
- Risco residual: zero de Hermes representa somente custo de API externa, não hardware/energia; OpenRouter omitido permanece desconhecido. A imagem worker ainda contém pip antigo, risco operacional já documentado.

## QA-006 — Recursos de ciclo de IA sem contrato completo

- Área/severidade: IA/funcional — **ALTO**
- Estado: **RESOLVIDO** em `cb48c6c`.
- Atual anterior: existiam criar, listar, consultar, regenerar e feedback. Não havia endpoints para cancelar geração, aplicar alternativa a conteúdo ou chave de idempotência; concorrência não tinha evidência.
- Risco: duplicidade, falta de cancelamento e jornada incompleta entre geração e conteúdo versionado.
- Recomendação: definir critérios antes de implementar e manter aprovação humana.
- Regressão: concorrência, repetição com idempotency key, cancelamento e aplicação criando versão sem publicação.
- Causa raiz: o ciclo terminava na geração e não persistia chave/fingerprint da requisição, estado de cancelamento nem vínculo entre alternativa e versão de conteúdo.
- Correção: criação e regeneração aceitam idempotência tenant-scoped; repetição igual retorna o mesmo recurso e payload divergente recebe 409. O banco possui unicidade para múltiplos processos e o serviço serializa chaves no processo. Cancelamento é idempotente e auditado. Aplicação é idempotente, cria exatamente um conteúdo `DRAFT` e uma versão, preserva autoria, sensibilidade e vínculo, sem approval ou publicação.
- Evidências: migration `0017_ai_lifecycle`; testes positivos, inválidos, concorrentes, idempotentes, sem permissão, outro tenant, inexistentes e auditados em `test_ai_lifecycle.py`; fluxo E2E offline ampliado.
- Risco residual: o cancelamento invalida uma geração já concluída porque a execução atual é síncrona; ele não interrompe uma chamada HTTP em andamento. A proteção local usa locks particionados e a garantia entre processos permanece no PostgreSQL.

## QA-007 — Hermes aparece configurado sem healthcheck efetivo

- Área/severidade: Providers/operação — **MÉDIO**
- Classificação de release: **ACCEPTABLE FOR CONTROLLED PILOT** e **MUST FIX BEFORE REAL DATA**.
- Estado: **RISCO ACEITO SOMENTE PARA PILOTO FICTÍCIO**, em 2026-08-07.
- Atual: presença de `HERMES_BASE_URL` marca configuração; Ollama estava indisponível e só foi detectado durante geração/fallback.
- Causa raiz confirmada: o Compose define URL local padrão e a listagem deriva `configured_by_environment` apenas da presença da URL. O teste consulta `/api/tags` e retorna `UNAVAILABLE`, mas sem linha persistida a listagem volta a `NOT_CHECKED`.
- Risco: painel sugere disponibilidade inexistente e adiciona latência.
- Impacto de release: não bloqueia piloto interno com Hermes declarado indisponível, OpenRouter prioritário e Mock obrigatório; bloqueia operação com dados reais por prejudicar observabilidade e resposta a falhas.
- Recomendação: diferenciar configurado, saudável e modelo instalado; cachear healthcheck sem expor detalhes.
- Regressão: Ollama falso saudável, modelo ausente, timeout e resposta inválida.
- Esforço/risco de regressão: 1–2 dias; risco médio em rede, cache e painel.

## QA-008 — CSP permite `unsafe-inline`

- Área/severidade: Segurança frontend — **MÉDIO**
- Classificação de release: **ACCEPTABLE FOR CONTROLLED PILOT** e **MUST FIX BEFORE REAL DATA**.
- Estado: **RISCO ACEITO SOMENTE PARA PILOTO FICTÍCIO**, em 2026-08-07.
- Evidência: cabeçalho da página `/login`.
- Causa raiz confirmada: a CSP estática do Next.js permite scripts e estilos inline para compatibilidade de renderização; nonce/hash por requisição ainda não foi implementado.
- Risco: reduz a proteção contra XSS caso outra barreira falhe.
- Impacto de release: não bloqueia uso local, restrito e com dados fictícios; bloqueia exposição pública ou uso de dados reais sem CSP endurecida e TLS/HSTS validados.
- Recomendação: avaliar nonce/hash no deploy de produção; manter compatibilidade Next.js documentada.
- Regressão: teste de headers por ambiente.
- Esforço/risco de regressão: 2–4 dias; risco médio/alto de quebrar hidratação ou estilos.

## QA-009 — Lista de conteúdos é o endpoint mais pesado medido

- Área/severidade: Desempenho — **MÉDIO**
- Classificação de release: **ACCEPTABLE FOR CONTROLLED PILOT** e **MUST FIX BEFORE REAL DATA**.
- Estado: **RISCO ACEITO SOMENTE PARA PILOTO FICTÍCIO**, em 2026-08-07.
- Atual: após crescimento da base local, 187.551 bytes, p50 entre 372,2 e 460,9 ms e p95 entre 420,9 e 719,3 ms em duas séries de 10 amostras.
- Causa raiz confirmada: a listagem serializa até 50 conteúdos com versão, aprovações e revisões completas; o custo cresce com volume e payload.
- Risco: degradação em bases maiores e mobile.
- Impacto de release: ainda passa o orçamento local de 750 ms, mas está próximo do limite; aceitável apenas com base pequena e monitoramento, não para escala/dados reais.
- Recomendação: revisar payload, paginação real, índices e queries antes do piloto ampliado.
- Regressão: orçamento de payload e p95 com volume representativo.
- Esforço/risco de regressão: 2–4 dias; risco médio por alterar read model e contrato de listagem.

## QA-010 — Ambiente de desenvolvimento incompleto para auditoria Python isolada

- Área/severidade: Instalação — **BAIXO**
- Classificação de release: **BACKLOG**.
- Estado: **RISCO ACEITO**; não afeta runtime.
- Atual: `python3.12-venv`/ensurepip ausente; criação de venv isolado falhou. A CI executou pip-audit com sucesso.
- Causa raiz/impacto: pacote opcional do host não instalado; reduz conveniência local, mas Docker e CI permanecem reproduzíveis.
- Recomendação: confirmar pré-requisito no README/doctor ou oferecer alvo Docker isolado.
- Esforço/risco de regressão: horas; baixo.

## QA-011 — Buildx ausente gera warnings repetidos

- Área/severidade: Operação — **MELHORIA**
- Classificação de release: **BACKLOG**.
- Estado: **RISCO ACEITO**.
- Atual: Compose usa Bake, mas buildx não está instalado; build cai para driver padrão e funciona.
- Causa raiz/impacto: plugin opcional ausente neste host; produz ruído e build mais lento, sem falha funcional.
- Recomendação: documentar buildx como opcional ou eliminar o aviso.
- Esforço/risco de regressão: horas; baixo.

## QA-012 — `js-yaml` com vulnerabilidade alta no frontend

- Área/severidade: Dependências frontend — **ALTO**
- Estado: **RESOLVIDO** em `cd7fc31`.
- Atual anterior: `npm --prefix frontend audit --audit-level=high` apontava CVE-2026-59870/GHSA-5p4m-2wfm-xmqj em `js-yaml` 4.3.0.
- Risco: consumo quadrático de CPU ao resolver `!!omap` caso entrada YAML não confiável alcance a dependência vulnerável; a explorabilidade no produto ainda não foi analisada.
- Causa raiz: `eslint@9.39.5` dependia de `@eslint/eslintrc@3.3.6`, que aceitava `js-yaml ^4.3.0`; o lockfile ainda fixava a versão vulnerável 4.3.0. Era uma dependência transitiva de desenvolvimento, sem uso no runtime ou em YAML recebido pelo produto.
- Correção: o lockfile passou a resolver `js-yaml` 4.3.1, primeira versão corrigida dentro da faixa já aceita pelo pacote pai. Não houve atualização de framework, dependência direta, override ou `--force`.
- Evidências: instalação limpa com `npm ci`; `npm ls` confirmou a árvore ESLint → `@eslint/eslintrc` → `js-yaml@4.3.1`; audits de frontend e E2E retornaram zero vulnerabilidades; lint, tipos, build, 240 backend, 41 worker, 54 frontend e 10 E2E passaram.
- CI: run 31149722340 integralmente verde em `cd7fc31`, incluindo auditoria npm, build, migrações e E2E offline.
- Risco residual: a dependência permanece na ferramenta de lint, não no runtime. Atualizações futuras do lockfile devem manter o audit impeditivo. O aviso de Node 20 das actions v4 e os riscos QA-007 a QA-011 são independentes desta correção.

## Contagem após QA-012

- resolvidos/mitigados: 7 (QA-001 a QA-006 e QA-012);
- abertos altos: 0;
- abertos médios: 3 (QA-007 a QA-009);
- aberto baixo: 1 (QA-010);
- melhoria: 1 (QA-011);
- bloqueadores/críticos abertos: 0.
