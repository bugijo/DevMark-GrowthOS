# Custos dos providers de IA

## Contrato

Valores monetários usam `Decimal` no domínio e `Numeric(18, 8)` no PostgreSQL,
sempre com moeda explícita. O estado distingue:

- `CONFIRMED`: o provider retornou `usage.cost`, inclusive zero;
- `ESTIMATED`: o provider retornou explicitamente `usage.estimated_cost`;
- `UNKNOWN`: campo ausente, nulo ou inválido; nunca é convertido em zero.

A origem registra `PROVIDER_USAGE_COST`, `PROVIDER_USAGE_ESTIMATE` ou
`INVALID_PROVIDER_VALUE`. O adaptador aceita número ou string decimal não
negativa e finita. Float binário não é usado para persistência nem agregação.

OpenRouter é a única integração externa inicial que informa custo monetário na
resposta. O Mock registra custo externo zero confirmado pela política
`MOCK_EXTERNAL_COST_POLICY`. Hermes/Ollama registra custo de API externa zero
pela política `LOCAL_PROVIDER_EXTERNAL_COST_POLICY`; energia, hardware e
operação local não são estimados pelo sistema e não devem ser interpretados
como custo total zero.

## Persistência e agregação

Cada tentativa registra estado, valor, moeda, origem, provider, modelo e data.
A geração consolidada copia somente o resultado do provider que respondeu. O
uso diário soma custos confirmados e estimados em campos separados e conta
custos desconhecidos; `cost_accounted_at` impede aplicar a mesma geração duas
vezes. Fallback registra falhas como custo desconhecido e contabiliza o custo
do provider vencedor uma vez. Regeneração é uma nova geração e é agregada
separadamente.

Registros anteriores à migration `0016_ai_costs` permanecem com valor nulo,
estado `UNKNOWN` e não são reclassificados retroativamente.

## Apresentação e privacidade

A API serializa Decimal como texto para não perder precisão. A interface mostra
“confirmado”, “estimado” ou “custo não informado pelo provider”, sem inventar
casas decimais além das oito persistidas. Exportação LGPD e relatório por
período usam o mesmo contrato e respeitam organização e cliente.

A fixture de contrato OpenRouter é sanitizada: não contém chave, cookie, token,
prompt real nem dado de cliente. A suíte padrão usa transporte falso e não
acessa a internet.
