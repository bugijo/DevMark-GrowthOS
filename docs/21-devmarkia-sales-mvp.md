# DevMarkia — MVP comercial interno

## Estado

O código adiciona um pipeline interno multi-tenant para oportunidades DevMarkia:

`lead → contato → briefing → preparação de proposta → negociação → produção → entrega → pós-venda`

O acesso fica restrito a `SUPER_ADMIN`, `AGENCY_ADMIN` e `STRATEGIST`, com escopo obrigatório da organização. A proposta e o briefing são determinísticos (`ai_used=false`). Nenhuma mensagem, proposta, contrato, tarefa externa ou publicação é enviada automaticamente. O preço de referência de R$ 1.690 e o prazo de cinco dias úteis continuam condicionais e não vinculantes.

## Entrada pública

`PUBLIC_QUOTE_INTAKE_ENABLED=false` é o padrão. A rota `/orcamento` informa indisponibilidade sem coletar dados nesse estado. Para habilitá-la será necessário, além de configurar organização e aviso HTTPS, registrar aprovação jurídica e de segurança. Esses flags não comprovam criptografia em repouso nem conformidade: tais revisões precisam verificar a implantação real.

O rate limit atual é em memória e por processo. Antes de abrir intake em produção com múltiplas réplicas, deve ser substituído por mecanismo compartilhado. Também falta um fluxo verificado para titulares anônimos exportarem/excluírem os dados enviados; a retenção administrativa cobre exclusão por prazo, não substitui pedidos de titular. Não coletar leads reais até fechar esses itens e confirmar proteção do banco/backups, retenção e aviso legal.

## Privacidade e operação

- O CRM interno guarda dados pessoais na base GrowthOS; nenhuma garantia de criptografia em repouso foi assumida neste incremento.
- Auditoria guarda ação, etapa e referências, evitando nome, telefone, e-mail e conteúdo do lead.
- O middleware omite IP do log de acesso na rota pública de orçamento.
- `sales_leads` pode ser configurado em retenção, com dry-run como padrão; execução é explícita, auditada e limitada à organização.
- O endpoint público usa idempotência e resposta sem dados do lead; honeypot não persiste o conteúdo.
- Não executar a retenção na base operacional sem revisão da política e autorização do administrador.

## Caminho de ativação seguro

1. Validar escopo, custos reais, impostos, margem e disponibilidade antes de oferecer preço/prazo.
2. Usar o pipeline apenas com leads internos/autorizados durante a preparação.
3. Aprovar aviso e base legal com responsável jurídico; validar armazenamento, backups, acesso e rate limit compartilhado com responsável técnico.
4. Implementar e testar exportação/exclusão de titulares para solicitações públicas; definir retenção.
5. Somente então aprovar e configurar intake público, publicar a página e monitorar a coleta.

Não existe integração com Hermes Worker, OpenRouter, JEV ou envio externo neste MVP. Não houve alteração na pilha em execução nem em site público.
