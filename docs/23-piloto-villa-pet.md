# Piloto Villa Pet — preparação no GrowthOS

**Estado em 2026-10-27: demonstração local com dados fictícios.** Nada foi
publicado, enviado ou cadastrado com dados reais de clientes da Villa Pet.

## Dois fluxos distintos

1. **DevMarkia → Villa Pet (venda do serviço).** A Villa Pet é o lead comercial
   da agência. Usa o pipeline existente (`docs/21-devmarkia-sales-mvp.md`):
   lead → contato → briefing → proposta em rascunho não enviada → tarefa de
   acompanhamento. **Pronto e demonstrável hoje.**
2. **Villa Pet → tutores (agendamento de banho e tosa).** Os tutores são leads
   da Villa Pet. O GrowthOS **não** tem módulo de agendamento; este fluxo
   precisa de decisão antes de ser construído (ver “Pendências”).

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

## Preços de referência da Villa Pet

| Porte   | Referência recebida |
|---------|---------------------|
| Pequeno | R$ 55               |
| Médio   | R$ 75               |
| Grande  | R$ 95               |

Valores a confirmar pelo responsável antes de qualquer peça pública. Não há
pacotes, descontos, duração, formas de pagamento ou política de cancelamento
definidos; nenhum desses itens deve ser presumido.

## Pendências para o fluxo 2

- Decidir onde o registro de tutores será armazenado e quem acessa
  (`VILLA_PET_CAMPANHA_APROVACAO.md`, “Aprovação humana pendente”).
- Se for no GrowthOS: novo módulo por `business_id` com origem
  (`instagram_post`, `instagram_story`, `indicacao`, `whatsapp_direto`,
  `outro`), porte, serviço, preferências de data/período, consentimento e
  estados `novo`, `aguardando_dados`, `horario_ofertado`, `confirmado`,
  `realizado`, `cancelado`, `nao_compareceu`; preço registrado como
  referência no momento do pedido, nunca como cobrança.
- O mesmo gate de privacidade de `docs/22-gate-privacidade-ativacao-comercial.md`
  se aplica: sem aviso legal, base legal e retenção, apenas dados fictícios.
