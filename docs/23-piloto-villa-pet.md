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

## Pendências antes de captação real

- Responsável da Villa Pet confirmar preços, serviços, endereço, canal oficial
  e aprovar textos (`VILLA_PET_CAMPANHA_APROVACAO.md`).
- Gate de privacidade (`docs/22-gate-privacidade-ativacao-comercial.md`):
  aviso legal, base legal, retenção, exportação/exclusão por titular e rate
  limit compartilhado. Só então adicionar campos de contato com consentimento
  e desligar `demo_mode`.
- Usuário-cliente da Villa Pet para aprovar conteúdos e ver seus interessados
  (hoje as rotas de interessados usam as capabilities comerciais da agência).
- Hospedagem pública com HTTPS e domínio; hoje tudo roda só em `127.0.0.1`.
