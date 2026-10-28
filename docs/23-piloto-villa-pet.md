# Piloto Villa Pet — preparação no GrowthOS

**Estado em 2026-10-27: demonstração local com dados fictícios.** Nada foi
publicado, enviado ou cadastrado com dados reais de clientes da Villa Pet.

## Dois fluxos distintos

1. **DevMarkia → Villa Pet (venda do serviço).** A Villa Pet é o lead comercial
   da agência. Usa o pipeline existente (`docs/21-devmarkia-sales-mvp.md`):
   lead → contato → briefing → proposta em rascunho não enviada → tarefa de
   acompanhamento. **Pronto e demonstrável hoje.**
2. **Villa Pet → tutores (pedido de banho e tosa).** Os tutores são
   interessados da Villa Pet. Implementado como módulo genérico por negócio
   cliente (migração `0019_landing_leads`): landing page com aprovação humana e
   painel de interessados. **Demonstrável com dados fictícios** (ver abaixo).

## Demonstração do fluxo 2 (landing → interessado → acompanhamento)

Com o stack local em `0019_landing_leads`:

```bash
python3 scripts/demo-villa-pet.py
```

O script cria, se faltar, o cliente Villa Pet, o perfil de marca, a landing em
**rascunho** e três conteúdos de campanha pelo gerador mock. A aprovação é
humana, na tela `/landing`.

- **Painel** `/landing` (agência): editar a página, ver prévia (envio
  desativado), aprovar a versão exata revisada, revogar a publicação e
  acompanhar interessados (status com transições permitidas, próxima ação,
  contadores de ações pendentes/atrasadas). Registro manual aceita só dados
  fictícios.
- **Página** `/p/villa-pet`: só existe após aprovação; qualquer edição ou
  revogação a tira do ar na hora.
- **Formulário demonstrativo**: apenas escolhas fechadas (serviço, porte,
  período, origem). A API rejeita com 422 qualquer campo extra como nome,
  telefone ou e-mail, e a tabela `business_leads` não tem colunas de contato.
  Todo registro é `is_demo=true`; nada é enviado.
- **Campanha**: conteúdos em `/conteudos` seguem o fluxo existente de revisão
  interna e aprovação do cliente; publicação continua manual.
- **Acompanhamento para o Hermes**: `GET /businesses/{id}/leads/summary`
  resume totais, status, origens, ações sem dono e ações atrasadas.
- Auditoria: `landing_page.created/updated/approved/revoked`,
  `business_lead.demo_created/created/updated`.
- Rede: todas as portas do stack estão ligadas a `127.0.0.1`; a página não é
  acessível pela LAN nem pela internet.

## Demonstração do fluxo 1

Com o stack local em `0018_sales_leads` ou superior:

```bash
python3 scripts/demo-sales-pipeline.py
```

O script aceita apenas URLs locais, lê as credenciais demo do `.env` sem
imprimi-las e cria um lead `MANUAL` com contato fictício
(`contato.villapet@example.test`). A proposta permanece `DRAFT_NOT_SENT` e o
texto de referência (R$ 1.690, cinco dias úteis) continua condicional e não
vinculante. Cada execução cria um novo lead de demonstração.

### Validação registrada em 2026-10-27

Stack local em `0018_sales_leads`, frontend reconstruído com `/comercial`:

- API: script acima concluído (lead `MANUAL`, briefing `ai_used=false`,
  proposta `DRAFT_NOT_SENT`, uma tarefa de acompanhamento).
- Navegador, perfil agência demo: lista de oportunidades, detalhe do lead,
  “Preparar briefing” e “Rascunho de proposta” exibiram “Rascunho interno
  criado; nada foi enviado.” O botão “Registrar envio manual” apenas move a
  etapa para `PROPOSAL_SENT`; o serviço de vendas não tem caminho de e-mail
  ou WhatsApp.
- Dados: um único lead (`contato.villapet@example.test`); usuários apenas em
  `@devmark.local`, `@clinicafeliz.local` e `@example.test`.
- Coleta pública: `/api/v1/public/quote-requests/config` retorna
  `enabled=false`; POST válido retorna 404 sem gravar. Mailpit: 0 mensagens.

## Preços de referência da Villa Pet

| Porte   | Referência recebida |
|---------|---------------------|
| Pequeno | R$ 55               |
| Médio   | R$ 75               |
| Grande  | R$ 95               |

Valores a confirmar pelo responsável antes de qualquer peça pública. Não há
pacotes, descontos, duração, formas de pagamento ou política de cancelamento
definidos; nenhum desses itens deve ser presumido.

## Operação da Villa Pet (preparada em 2026-10-28)

| Peça | Onde | Quem |
| --- | --- | --- |
| Usuário do responsável (`CLIENT_OWNER`, limitado à Villa Pet) | `growthos-pilot-client --org devmark-demo --business "Villa Pet"` | agência provisiona |
| Aprovação de conteúdos | `/aprovacoes` (fluxo existente `CONTENT_DECIDE_CLIENT`) | responsável |
| Painel de solicitações, status e próxima ação | `/solicitacoes` | responsável e agência; revisor só consulta |
| Horários de atendimento | `/atendimento` — começa vazio, nada é sugerido | responsável e agência |
| Aviso de privacidade | `/atendimento` — agência redige, **só o responsável aprova** | ambos |
| Exportar / anonimizar pedido, retenção | `/solicitacoes`, `/atendimento` | responsável e administração da agência |
| Auditoria | toda ação grava `audit_logs`, sem nome ou telefone | — |

Credencial demo do responsável: `DEMO_PILOT_CLIENT_EMAIL` /
`DEMO_PILOT_CLIENT_PASSWORD` do `.env.example` (valores locais, trocar antes de
qualquer uso real).

### Portões para pedidos reais

`POST /public/landing/{slug}/requests` aceita nome e telefone **somente** com os
três portões abertos; hoje todos estão fechados:

1. `PUBLIC_LEAD_COLLECTION_ENABLED=true`, que a configuração recusa sem
   `PUBLIC_LEAD_LEGAL_REVIEW_APPROVED` e `PUBLIC_LEAD_SECURITY_REVIEW_APPROVED`
   (declarações de revisão humana);
2. aviso de privacidade do estabelecimento aprovado pelo responsável, na versão
   exibida ao tutor (o pedido carrega a versão aceita);
3. landing fora do modo demonstração (não há botão para isso ainda — é uma
   decisão a tomar depois da revisão).

Proteções já implementadas: `extra="forbid"`, limite por IP e página, campo-isca
contra robôs (descarta e audita), deduplicação por telefone em 24 h, validação
de telefone, contato fora da auditoria e da integração com o Hermes.

Aprovar o aviso **não** declara conformidade com a LGPD: a tela e a API exigem
reconhecer que a aprovação é do estabelecimento e não substitui revisão
jurídica.

### Direitos do titular e retenção

- Exportação: `GET /business-leads/{id}/export` (dados + histórico de ações).
- Anonimização: `POST /business-leads/{id}/anonymize` apaga nome, telefone,
  observações e próxima ação; mantém serviço/status para estatística.
- Retenção: `POST /businesses/{id}/leads/retention` com `dry_run` (padrão
  `true`); usa os dias definidos no aviso. Execução manual, sem agendamento.

### Hermes como supervisor

O Hermes lê com token `leads:read` + `contents:read` (contagens de conteúdos
pendentes, sem texto) e gera um relatório local sob demanda:
`python3 ~/.hermes/dev-controller/growthos_report.py [--save]`. Não há envio
automático por nenhum canal.

## Pendências antes de captação real

- Responsável da Villa Pet confirmar preços, serviços, endereço, canal oficial
  e aprovar textos (`VILLA_PET_CAMPANHA_APROVACAO.md`).
- Revisão jurídica humana do aviso e da base legal; o responsável aprova o
  texto final em `/atendimento`.
- Responsável informar os horários reais em `/atendimento`.
- Rate limit compartilhado entre réplicas (hoje é em memória, por processo).
- Decidir quem desliga `demo_mode` e como (não existe ação para isso ainda).
- Hospedagem pública com HTTPS e domínio; hoje tudo roda só em `127.0.0.1`.
