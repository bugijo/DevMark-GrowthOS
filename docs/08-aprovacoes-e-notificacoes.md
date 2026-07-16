# Aprovações e notificações

## Objetivo

O fluxo de aprovação garante que nenhum conteúdo saia do controle da equipe e do cliente. A versão em análise, a decisão, o autor e o momento da ação devem ser inequívocos e auditáveis.

O primeiro fluxo vertical entregou revisão interna, decisão do cliente,
notificação interna e audit log. A Fase 2 acrescenta decisão independente de
texto/imagem e e-mail pelo Mailpit local. Preferências e resumos permanecem para
uma etapa posterior da versão 1.0.

## Estados oficiais do conteúdo

- `DRAFT`: rascunho editável.
- `INTERNAL_REVIEW`: aguardando revisão da agência.
- `CLIENT_REVIEW`: versão fechada aguardando decisão do cliente.
- `CHANGES_REQUESTED`: o cliente ou revisor solicitou ajuste.
- `APPROVED`: versão aprovada pelo cliente.
- `SCHEDULED`: marcada no calendário; não significa publicação automática.
- `PUBLISHED`: publicação confirmada por registro manual na versão 1.0.
- `FAILED`: uma operação autorizada falhou.
- `ARCHIVED`: item encerrado e fora do fluxo ativo.

## Transições permitidas

| Origem | Destino | Quem pode executar | Condição principal |
|---|---|---|---|
| `DRAFT` | `INTERNAL_REVIEW` | editor, estrategista ou admin | versão válida |
| `INTERNAL_REVIEW` | `DRAFT` | revisor interno | correção interna |
| `INTERNAL_REVIEW` | `CLIENT_REVIEW` | revisor interno ou admin | revisão interna concluída |
| `CLIENT_REVIEW` | `APPROVED` | `CLIENT_OWNER` ou `CLIENT_REVIEWER` | decidir sobre a versão atual |
| `CLIENT_REVIEW` | `CHANGES_REQUESTED` | `CLIENT_OWNER` ou `CLIENT_REVIEWER` | comentário de alteração obrigatório |
| `CLIENT_REVIEW` | `ARCHIVED` | `CLIENT_OWNER` ou `CLIENT_REVIEWER` | decisão de reprovar e motivo obrigatório |
| `CHANGES_REQUESTED` | `DRAFT` | editor ou admin | criar nova versão |
| `APPROVED` | `SCHEDULED` | equipe interna autorizada | data definida; sem publicar |
| `SCHEDULED` | `PUBLISHED` | equipe interna autorizada | confirmação manual na versão 1.0 |
| qualquer estado ativo | `ARCHIVED` | admin autorizado | confirmação e motivo |

Transições fora da tabela são recusadas pela camada de domínio, não apenas escondidas na interface. Reabrir um item aprovado cria novo ciclo e nova versão; não altera silenciosamente a versão já aprovada.

`Salvar para depois` não muda o status nem decide a aprovação: mantém o item em `CLIENT_REVIEW`, registra a ação e ajusta apenas a experiência de lembrete quando aplicável. `Reprovar` registra a decisão `REJECTED` e arquiva o item, pois `REJECTED` não é um status oficial de conteúdo.

## Unidade de aprovação

A decisão sempre aponta para um `content_item` e para uma `content_version` específica. O registro de aprovação deve guardar:

- `organization_id` e `business_id`;
- versão avaliada;
- componente avaliado (`TEXT` ou `IMAGE`);
- decisão (`APPROVED`, `CHANGES_REQUESTED` ou `REJECTED`, quando adotada);
- autor e papel no momento da decisão;
- data e hora;
- comentário e motivo, quando aplicável;
- snapshot ou hash do conteúdo avaliado;
- origem da ação e identificador de correlação.

Após o envio ao cliente, aquela versão fica imutável. Texto e imagem possuem
decisões próprias; o conteúdo só chega a `APPROVED` quando os dois componentes
da versão atual estão aprovados. Qualquer alteração cria nova versão e invalida
a decisão pendente anterior de forma explícita. A API evita decisões duplicadas
com transação, controle de concorrência e unicidade por
`(versão, etapa, componente)`.

## Fluxo de revisão

1. A equipe cria ou ajusta o rascunho.
2. O conteúdo entra em revisão interna.
3. Um usuário interno autorizado confere texto, visual, Brand Kit e riscos.
4. Conteúdo veterinário ou de saúde exige confirmação de revisão profissional.
5. A versão fechada entra em `CLIENT_REVIEW`.
6. O sistema cria notificação para os revisores autorizados da empresa.
7. O cliente aprova, pede alteração, reprova ou salva a decisão para depois em poucos toques.
8. Pedido de alteração volta ao editor, preservando todo o histórico.
9. A nova versão percorre novamente as revisões necessárias.
10. A aprovação permite calendário e registro manual de publicação, nunca publicação automática na versão 1.0.

`CLIENT_REVIEWER` pode aprovar e pedir alteração. `VIEWER` apenas consulta. A API valida associação à organização, vínculo com a empresa e papel em todas as ações.

## Notificações da versão 1.0

### Canais

- **Interno:** obrigatório e persistido no banco, com contador de não lidas.
- **E-mail:** executado pelo worker; desenvolvimento usa SMTP local capturado no Mailpit.
- **WhatsApp, push, Telegram e Slack:** futuros e desativados.

### Eventos mínimos

- conteúdo enviado para revisão interna;
- conteúdo enviado ao cliente;
- pedido de alteração;
- nova versão disponível;
- conteúdo aprovado ou rejeitado;
- comentário com menção, quando implementado;
- falha importante de job;
- lembrete de aprovação configurado.

### Preferências

O alvo da versão 1.0 permite aviso imediato, resumo diário, resumo semanal ou somente itens importantes. Preferências nunca autorizam ações externas: elas alteram somente frequência e canal. Um aviso urgente pode ser imediato quando permitido, sem ignorar consentimento ou endereço validado.

## Entrega segura e confiável

- Criar a notificação na mesma transação lógica da mudança de estado ou por padrão outbox, evitando estado alterado sem evento registrado.
- Processar e-mail no worker, com tentativas limitadas, atraso crescente e status visível.
- Não repetir e-mail por reprocessamento do mesmo evento; usar chave idempotente.
- Persistir no job somente a referência da notificação; o worker revalida
  organização, empresa, usuário e membership ativa antes de resolver o e-mail.
- Falha de e-mail não desfaz uma aprovação válida, mas gera alerta interno e possibilidade de nova tentativa.
- Não incluir segredo, conteúdo clínico, token de sessão ou dado excessivo no e-mail.
- Links por e-mail direcionam ao login; tokens de convite ou recuperação têm uso único e expiração.
- Toda consulta e marcação como lida respeita `organization_id` e destinatário.

## Audit log

Registrar, no mínimo:

- criação e edição de versão;
- entrada e saída de cada etapa de revisão;
- envio, cancelamento ou expiração de solicitação;
- decisão do revisor;
- comentário e pedido de alteração;
- criação e tentativa de entrega da notificação;
- registro manual de publicação;
- mudança de responsável ou permissão.

O audit log é append-only para usuários comuns e respeita capacidades: agência
consulta a organização, papéis internos veem recursos autorizados e papéis de
cliente ficam limitados à própria empresa; `VIEWER` não acessa esse histórico.
Não deve armazenar senha, token, segredo, URL assinada ou corpo completo
desnecessário. Comentários livres ficam na decisão, não são duplicados nos
metadados do audit log.

## Política de autonomia

- Leitura de pendências e criação de notificações internas podem ocorrer automaticamente após evento autorizado.
- Enviar conteúdo ao cliente exige ação de usuário interno autorizado.
- Aprovação nunca é presumida por silêncio, prazo vencido ou resposta de provider.
- Agentes e providers não podem aprovar em nome de pessoas.
- Publicar, responder mensagens, alterar perfis, campanhas ou orçamento exige aprovação explícita e está fora do fluxo automático da versão 1.0.
- Escrita automática controlada só poderá existir em versão futura, com política aprovada, limites, reversão, alerta, auditoria e bloqueio de emergência.

## Critérios de aceite

1. **AP-01:** somente transições previstas são aceitas pelo backend.
2. **AP-02:** uma versão em `CLIENT_REVIEW` permanece imutável.
3. **AP-03:** um revisor autorizado consegue aprovar, pedir alteração, reprovar ou salvar para depois no celular em poucos toques.
4. **AP-04:** `VIEWER` e usuários sem vínculo recebem negação ao tentar decidir.
5. **AP-05:** manipular `organization_id`, `business_id` ou o identificador da versão não permite acesso cruzado.
6. **AP-06:** pedir alteração exige justificativa e cria um novo ciclo sem apagar a versão anterior.
7. **AP-07:** toda decisão registra usuário, data, papel e versão exata.
8. **AP-08:** o envio a `CLIENT_REVIEW` cria notificação interna para os destinatários corretos.
9. **AP-09:** o contador de pendências reflete apenas itens não lidos ou pendentes do usuário autenticado.
10. **AP-10:** repetir a mesma requisição idempotente não duplica decisão nem notificação.
11. **AP-11:** falha do adaptador de e-mail fica registrada e pode ser repetida sem invalidar a decisão.
12. **AP-12:** conteúdo sensível não avança sem registro de revisão profissional.
13. **AP-13:** aprovação não dispara publicação social ou gasto.
14. **AP-14:** todas as etapas relevantes aparecem no audit log em ordem verificável.

## Fora do escopo desta etapa

- aprovação por WhatsApp, Telegram ou link público sem autenticação;
- publicação direta em Instagram ou Facebook;
- respostas automáticas a mensagens;
- aprovação automática por prazo ou regra de IA;
- campanhas em massa;
- gasto ou alteração automática de orçamento;
- assinatura eletrônica com validade jurídica específica.
