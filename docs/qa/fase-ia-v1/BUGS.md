# Bugs — Fase IA v1

## QA-001 — Drift de nove constraints bloqueia CI

- Área/severidade: Banco e CI — **BLOQUEADOR**
- Ambiente/perfil: banco PostgreSQL limpo; operador/CI
- Pré-condição: aplicar migrations até `0014_ai_generations`.
- Reprodução: executar `alembic upgrade head` e `alembic check`.
- Esperado: nenhum upgrade pendente.
- Atual: exit 255; Alembic sugere remover nove checks de notificações e revisão profissional.
- Evidência: CI run 30973261873, job 92201933568; reprodução em bancos `growthos_qa_base` e `growthos_qa_0008`.
- Risco: CI vermelha e divergência entre schema executável e metadata ORM.
- Recomendação: declarar as nove constraints no metadata ou alinhar migrations por migration aditiva; não editar migrations compartilhadas.
- Regressão: base→head, 0008→head, `alembic check`, downgrade base e novo upgrade.

## QA-002 — Suítes offline chamam OpenRouter real

- Área/severidade: IA/testes/privacidade — **CRÍTICO**
- Ambiente/perfil: host com `.env`, chave válida e `AI_EXTERNAL_ENABLED=true`; QA/desenvolvedor
- Reprodução: `make test` ou `make e2e`.
- Esperado: providers falsos/Mock, sem internet e sem custo.
- Atual: backend retorna `provider=openrouter`; teste backend leva ~46 s e falha. E2E offline também recebe OpenRouter. Com `AI_EXTERNAL_ENABLED=false`, 214 backend e 10 E2E passam.
- Evidência: `test_ai_generation_uses_offline_mock_and_records_history` e `ai-offline.spec.ts`.
- Risco: envio involuntário de fixtures/contexto, consumo de cota e suíte não determinística.
- Recomendação: configuração de teste deve sobrescrever explicitamente IA externa e chave; providers devem ser injetados/falsificados nos testes.
- Regressão: executar suítes com uma chave canário e provar, por servidor falso/contador, zero chamadas externas.

## QA-003 — `.env` local com modo 777

- Área/severidade: Segredos — **CRÍTICO**
- Ambiente/perfil: host Linux local; qualquer usuário/processo do host
- Reprodução: `stat -c '%a' .env` ou `make doctor`.
- Esperado: `600`.
- Atual: `777`.
- Risco: leitura e alteração da chave OpenRouter e demais segredos locais por terceiros.
- Recomendação: aplicar `chmod 600 .env` e tornar o doctor impeditivo quando houver segredo e permissões amplas.
- Regressão: doctor deve falhar ou alertar em severidade alta para modos com grupo/outros.

## QA-004 — LGPD não cobre snapshots de IA

- Área/severidade: LGPD/IA — **ALTO**
- Ambiente/perfil: organização com gerações; titular e administrador
- Reprodução: criar geração, solicitar exportação/anonimização e revisar `services/privacy.py`.
- Esperado: inventário, exportação, retenção e anonimização tratam instrução, feedback e `context_snapshot` conforme política.
- Atual: nenhuma referência a `AIGeneration`/snapshots no serviço e testes LGPD.
- Risco: exportação incompleta e retenção de contexto após solicitação administrativa.
- Recomendação: definir política legal e incluir entidades IA com preservação auditável mínima.
- Regressão: exportação e anonimização tenant-scoped com geração antes/depois.

## QA-005 — Custo do OpenRouter não é persistido

- Área/severidade: IA/controle de gasto — **ALTO**
- Ambiente/perfil: geração OpenRouter real; administrador
- Reprodução: gerar conteúdo e comparar resposta oficial com `estimated_cost_usd`.
- Esperado: custo retornado é salvo/exibido; ausência fica explícita.
- Atual: diagnóstico oficial retornou custo 0, mas provider não lê `usage.cost` e a aplicação persiste `null`.
- Risco: telemetria de gasto incompleta e limite financeiro não auditável.
- Recomendação: mapear custo somente quando fornecido, sem inventar valor.
- Regressão: provider falso com custo 0 e custo positivo, além de ausência do campo.

## QA-006 — Recursos de ciclo de IA sem contrato completo

- Área/severidade: IA/funcional — **ALTO**
- Atual: existem criar, listar, consultar, regenerar e feedback. Não foram encontrados endpoints para cancelar geração, aplicar alternativa a conteúdo ou chave de idempotência; concorrência não tem evidência.
- Risco: duplicidade, falta de cancelamento e jornada incompleta entre geração e conteúdo versionado.
- Recomendação: definir critérios antes de implementar e manter aprovação humana.
- Regressão: concorrência, repetição com idempotency key, cancelamento e aplicação criando versão sem publicação.

## QA-007 — Hermes aparece configurado sem healthcheck efetivo

- Área/severidade: Providers/operação — **MÉDIO**
- Atual: presença de `HERMES_BASE_URL` marca configuração; Ollama estava indisponível e só foi detectado durante geração/fallback.
- Risco: painel sugere disponibilidade inexistente e adiciona latência.
- Recomendação: diferenciar configurado, saudável e modelo instalado; cachear healthcheck sem expor detalhes.
- Regressão: Ollama falso saudável, modelo ausente, timeout e resposta inválida.

## QA-008 — CSP permite `unsafe-inline`

- Área/severidade: Segurança frontend — **MÉDIO**
- Evidência: cabeçalho da página `/login`.
- Risco: reduz a proteção contra XSS caso outra barreira falhe.
- Recomendação: avaliar nonce/hash no deploy de produção; manter compatibilidade Next.js documentada.
- Regressão: teste de headers por ambiente.

## QA-009 — Lista de conteúdos é o endpoint mais pesado medido

- Área/severidade: Desempenho — **MÉDIO**
- Atual: 135.082 bytes, p50 329,4 ms, p95/máximo 410,3 ms em 10 amostras locais.
- Risco: degradação em bases maiores e mobile.
- Recomendação: revisar payload, paginação real, índices e queries antes do piloto ampliado.
- Regressão: orçamento de payload e p95 com volume representativo.

## QA-010 — Ambiente de desenvolvimento incompleto para auditoria Python isolada

- Área/severidade: Instalação — **BAIXO**
- Atual: `python3.12-venv`/ensurepip ausente; criação de venv isolado falhou. A CI executou pip-audit com sucesso.
- Recomendação: confirmar pré-requisito no README/doctor ou oferecer alvo Docker isolado.

## QA-011 — Buildx ausente gera warnings repetidos

- Área/severidade: Operação — **MELHORIA**
- Atual: Compose usa Bake, mas buildx não está instalado; build cai para driver padrão e funciona.
- Recomendação: documentar buildx como opcional ou eliminar o aviso.
