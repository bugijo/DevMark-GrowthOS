# LGPD aplicada à camada de IA

## Escopo e formato de exportação

A exportação do titular usa o formato versionado `1.1`. A seção
`ai_generations` contém somente gerações solicitadas pelo usuário autenticado na
organização ativa. Consultas incluem simultaneamente `organization_id` e o
identificador do titular. Chaves, cookies, tokens, detalhes internos de erro e
payloads de outros usuários ou tenants não fazem parte do contrato.

Snapshots sanitizados continuam sendo tratados como potencialmente
identificáveis: podem reproduzir nomes de marca, públicos, instruções ou texto
fornecido por pessoas. Eles não são classificados automaticamente como dados
anônimos.

## Inventário e classificação

| Tabela/campo | Classificação | Exportação | Exclusão, anonimização e retenção |
|---|---|---|---|
| `ai_generations.requested_by_user_id` | pessoal; auditoria | implícito como titular da seção | convertido em `NULL`; evento LGPD preserva contagem, sem copiar o ID |
| `business_id`, `parent_generation_id`, tarefa e datas | técnico, potencialmente identificável e necessário à auditoria | sim, quando do titular | preservado durante a retenção operacional e removido somente com a geração |
| instrução adicional | pessoal/potencialmente identificável | sim | substituída por marcador na anonimização; esvaziada ao expirar snapshot |
| `context_snapshot` | potencialmente identificável | sim, somente o snapshot da geração do titular | substituído por marcador sem conteúdo na anonimização/retenção |
| provider, modelo, fallback, duração e status | técnico/auditoria | sim, exceto erro interno | preservado pelo período operacional |
| tokens e custo | técnico, uso e auditoria financeira | sim | agregado pode ser preservado sem identificador pessoal |
| `ai_generation_attempts` | técnico/auditoria | provider, modelo, status, duração e data; erro interno não | apagável pela política própria; erros podem ser minimizados separadamente |
| alternativas/resultados | potencialmente identificável | sim | payload substituído por marcador na anonimização; alternativas não aplicadas podem expirar |
| feedback, comentário e `user_id` | pessoal/potencialmente identificável | somente feedback do titular | `user_id` vira `NULL` e comentário recebe marcador; pode expirar por política |
| `ai_usage_daily` | agregado técnico | não na seção individual enquanto não houver atribuição ao titular | preservável legitimamente; política tenant-scoped pode expirar agregados antigos |
| `context_hash` | não existe no schema atual | não aplicável | qualquer inclusão futura exige revisão desta matriz antes da migration |
| referências diretas a conteúdo/estratégia | não existem no schema atual | não aplicável | a versão atual referencia empresa e geração pai; aplicação de alternativa está fora do contrato |

## Anonimização

Ao concluir uma solicitação de exclusão, a organização ativa é o limite da
operação. Gerações do titular perdem `requested_by_user_id`; instruções,
snapshots e resultados recebem marcadores sem o texto anterior. Feedback perde
`user_id` e comentário. Métricas diárias agregadas, tentativas técnicas e
relações de geração pai são preservadas para integridade e auditabilidade
mínimas. O audit log registra somente quantidades, decisão e responsável, nunca
o conteúdo removido.

O fundamento operacional é a minimização solicitada pelo titular, com
preservação de métricas agregadas e trilha mínima para execução contratual,
segurança e defesa de direitos. A política e o prazo são administrados pela
organização; decisões excepcionais exigem justificativa no registro de retenção.

## Retenção

As políticas aceitas para IA são `ai_generations`,
`ai_generation_attempts`, `ai_generation_alternatives`,
`ai_generation_feedback`, `ai_generation_snapshots`, `ai_usage_daily` e
`ai_generation_errors`. A execução exige `ORGANIZATION_MANAGE`, respeita o
tenant, recusa legal hold, oferece `dry_run`, é idempotente e gera audit log.

Como a versão atual não possui contrato de “alternativa aplicada”, a política
`ai_generations` contabiliza candidatos mas não apaga a geração consolidada.
Isso evita destruir evidência que possa sustentar histórico de aprovação. A
minimização deve ser feita por `ai_generation_snapshots`; exclusão definitiva
só poderá ser ativada depois que a aplicação de alternativa tiver vínculo
persistido e testado.
