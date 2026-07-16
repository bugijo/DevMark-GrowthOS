# Preferências e resumos de notificações

## Contrato da versão 1.0

Cada preferência pertence ao par `organization_id + user_id`. O e-mail pode ser
desativado globalmente e cada uma das oito categorias pode ser desativada ou
usar um dos modos `IMMEDIATE`, `DAILY`, `WEEKLY` e `URGENT_ONLY`. A notificação
interna continua sendo criada mesmo quando o e-mail não deve sair.

As categorias de conteúdo aguardando aprovação, estratégia aguardando aprovação
e falha de processamento são urgentes por padrão. `URGENT_ONLY` envia somente
essas ocorrências quando a notificação estiver marcada como `URGENT`; as demais
ficam apenas no portal. O worker consulta novamente a preferência, a categoria,
o usuário e a membership ativa imediatamente antes do SMTP. Uma alteração feita
depois do enqueue converte a entrega em `SKIPPED`, sem enviar mensagem.

## Horário, fuso e idempotência

Horário e dia da semana são interpretados no fuso IANA salvo pelo usuário. O
início de cada período é o slot local anterior, e não “24/168 horas antes” em
UTC. Assim, a mudança de horário de verão não cria lacunas nem sobreposição.
Quando o relógio pula um horário inexistente, usa-se o primeiro instante local
válido; quando repete um horário ambíguo, usa-se a segunda ocorrência.

O slot único é `organização + usuário + frequência + period_end`. Jobs, itens,
tentativas e resultado possuem chaves determinísticas ou restrições únicas. Um
retry depois de `DELIVERED` não chama o SMTP novamente. Falha antes da entrega
fica como `FAILED`, com código técnico sanitizado e audit log, e pode ser tentada
novamente pelo limite normal do worker.

## Compatibilidade de dados anteriores

A migration `0010` classifica decisões antigas como pedido de alteração quando
o título ou a mensagem persistida contém o radical “altera”; as demais decisões
legadas são classificadas como aprovação. Registros históricos com texto
customizado que não contenha esse indício são intrinsecamente ambíguos porque o
schema anterior não guardava a categoria. A migration não inventa uma decisão:
essa limitação permanece documentada e os novos registros recebem categoria
explícita na criação.
