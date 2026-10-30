# ADR 0006 — Growth Agent e fallback de IA

## Status

Aceita em 2026-08-04.

## Contexto

O produto precisa usar contexto real do cliente sem exigir provider pago e sem transformar IA em
publicação ou aprovação automática. A auditoria do Hermes Mobile confirmou que sua API atual não é
OpenAI-compatible e não integra Ollama.

## Decisão

Manter contratos de provider atrás do Growth Agent. A ordem é OpenRouter explicitamente ativado,
Ollama local pelo adapter Hermes e mock obrigatório. O adapter Ollama usa `/api/tags` e `/api/chat`.
Gerações, tentativas, alternativas, feedback e uso diário são persistidos por organização.

Saídas devem ser JSON validado. Falhas são registradas sem prompt ou segredo. Conteúdo sensível é
classificado novamente pelo guardrail local, e toda saída exige revisão humana.

## Consequências

O sistema funciona offline e não depende do contrato inexistente do Hermes Mobile. A ativação de
OpenRouter transfere contexto a terceiro e permanece bloqueada por padrão. O modelo Ollama deve ser
instalado fora do GrowthOS e sua indisponibilidade aciona fallback explícito.
