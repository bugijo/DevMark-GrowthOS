# Fase 2 da versão 1.0

**Status:** integrada à `main` em 2026-07-16 pelo squash
`3be89a7f8d62eecb7b29bdd665698ed2fbf2903c`, com stack, migrations, testes e CI
revalidados após o merge. Os critérios desta fase têm evidência, mas a release
1.0 ainda depende dos aceites remanescentes de `M6` e do hardening de `M7`.

## Objetivo

Completar o fluxo da clínica piloto sobre a fundação já aprovada, sem mudar a
arquitetura do monorepo e sem adicionar publicação automática ou integrações
reais com redes sociais, anúncios ou WhatsApp.

Esta fase transforma os cadastros básicos da fundação em um fluxo operacional:
equipe convidada com segurança, planejamento versionado, calendário, identidade
visual, mídia privada, aprovação separada de texto e imagem, publicação
registrada manualmente e relatório baseado somente em dados persistidos.

## Invariantes

- Toda entidade de negócio possui `organization_id`; entidades de cliente também
  possuem `business_id` quando aplicável.
- Toda leitura e escrita valida o tenant no banco. Identificadores enviados pelo
  navegador nunca definem sozinhos o escopo.
- Papéis de cliente permanecem limitados à empresa da membership ativa.
- Tokens de convite e recuperação são imprevisíveis, armazenados somente como
  hash, expiram e são consumidos uma única vez.
- Alterar senha, papel, escopo ou estado de membership incrementa a versão de
  sessão e invalida cookies emitidos antes da alteração.
- Versões submetidas para revisão são imutáveis. Uma alteração cria nova versão.
- Aprovações de texto e imagem são decisões independentes sobre a mesma versão.
- A API aceita decisões somente pelos endpoints granulares; o atalho legado que
  aprovava os dois componentes em uma chamada foi removido.
- Aprovação não publica conteúdo. `PUBLISHED` representa somente confirmação
  manual, auditada e idempotente.
- Arquivos ficam privados no storage. A API persiste a chave do objeto e produz
  URL assinada curta somente depois de autorizar o acesso.
- Providers mock são determinísticos e não usam chaves ou APIs pagas.
- O relatório nunca inventa alcance, impressões, cliques ou conversões.
- O portal cliente recebe o conteúdo liberado, mas não recebe notas, prompts,
  snapshots internos nem identificadores pessoais desnecessários.
- O seed vincula um PNG fictício real no storage privado ao conteúdo publicado;
  não cria aprovação visual apontando para um objeto inexistente.
- A compatibilidade com a fundação não transforma uma aprovação antiga sem
  mídia em aprovação visual: `0008` cancela esse componente, solicita revisão
  e audita a normalização.

## Papéis e capacidades

A matriz normativa continua sendo a de
[`06-agentes-e-responsabilidades.md`](06-agentes-e-responsabilidades.md). A API
implementa uma matriz central de capacidades com o seguinte recorte:

| Capacidade | Papéis autorizados |
| --- | --- |
| Administrar membros da agência | `SUPER_ADMIN`, `AGENCY_ADMIN` |
| Administrar usuários da própria empresa | `CLIENT_OWNER` |
| Editar marca, serviços e públicos | papéis internos conforme a matriz |
| Criar/revisar estratégia e calendário | `SUPER_ADMIN`, `AGENCY_ADMIN`, `STRATEGIST`, com edição operacional por `CONTENT_EDITOR` |
| Gerenciar preset e mídia | `SUPER_ADMIN`, `AGENCY_ADMIN`, `DESIGNER`; edição vinculada por `CONTENT_EDITOR` |
| Criar conteúdo textual | `SUPER_ADMIN`, `AGENCY_ADMIN`, `STRATEGIST`, `CONTENT_EDITOR` |
| Gerar prompt/revisão visual | equipe interna autorizada, incluindo `DESIGNER` |
| Decidir como cliente | somente `CLIENT_OWNER` e `CLIENT_REVIEWER` da empresa |
| Registrar publicação manual | equipe interna autorizada |
| Consultar relatório | papéis com leitura no próprio escopo |

`SUPER_ADMIN` não pode ser concedido por uma organização comum. Mudanças de
papel, escopo e estado da membership entram no audit log.

## Modelo de dados incremental

### Identidade

- `users.session_version`: versão incluída no token da sessão.
- `organization_invites`: e-mail normalizado, papel, empresa opcional, hash,
  expiração, aceite, revogação e autor do convite.
- `password_reset_tokens`: usuário, hash, expiração e consumo.

### Perfil e planejamento

- `services`, `audience_segments` e `marketing_objectives`: catálogos ativos por
  organização e empresa, preservados para histórico.
- `content_strategies`: raiz da estratégia e estado atual.
- `strategy_versions`: snapshots numerados com objetivo, público,
  posicionamento, pilares, funil, canais, indicadores e origem/provider.
- `content_plans`: período mensal com estratégia e estado.
- `calendar_entries`: pauta diária consultável por intervalo e, portanto,
  agrupável por mês ou semana.

### Visual, mídia e conteúdo

- `visual_presets`: contrato visual completo, com versão e modo de criação.
- `media_assets`: metadados verificados, checksum e chave privada no storage.
- `content_version_media`: vínculo ordenado entre versão e arquivo.
- `content_items` passa a referenciar estratégia, plano, pauta, preset e dados da
  publicação manual.
- `content_versions` recebe snapshots da marca/preset, roteiro, observações e
  prompts visuais.
- `approvals.component` distingue `TEXT` de `IMAGE`; a unicidade passa a ser por
  versão, etapa e componente.

## Contratos HTTP

Os contratos seguem o prefixo `/api/v1` e exigem sessão + CSRF em mutações,
exceto os endpoints públicos de solicitar/consumir recuperação e aceitar
convite.

- identidade: `/auth/password-recovery`, `/auth/password-reset`,
  `/auth/invitations/*`, `/members` e `/members/invitations`;
- catálogos: `/businesses/{id}/services`, `/audiences` e `/objectives`;
- planejamento: `/businesses/{id}/strategies`, `/strategies/{id}/versions`,
  transições de revisão, `/businesses/{id}/plans` e `/calendar`;
- visual e mídia: `/businesses/{id}/visual-presets`, `/visual-prompts/generate`,
  `/businesses/{id}/media` e `/media/{id}/download-url`;
- conteúdo: os contratos existentes permanecem compatíveis e recebem vínculos
  opcionais; decisões granulares usam
  `/contents/{id}/decisions/{component}/{approve|request-changes}` e revisões
  visuais usam `/contents/{id}/visual-revisions`;
- operação: `/contents/{id}/publication` e
  `/businesses/{id}/reports/period`.

## E-mail local

O Compose inclui uma caixa SMTP local de teste. Jobs de notificação guardam
somente `notification_id`; antes do SMTP, o worker reconsulta notificação,
usuário e membership ativa no mesmo tenant e escopo de empresa. Jobs de
convite/recuperação também guardam somente o identificador do registro, e o
worker deriva o token criptograficamente apenas ao montar o e-mail. O token
puro não é gravado no banco, no audit log nem nos logs do processo.

## Upload seguro

O backend aplica limite de bytes, lista de MIME permitidos, detecção por
assinatura, verificação do arquivo, nome de objeto aleatório, checksum e storage
privado. SVG e tipos executáveis não são aceitos. URLs assinadas não são
persistidas. Produção deverá adicionar varredura antimalware antes de liberar
arquivos fora do ambiente piloto.

## Critérios de aceite da fase

1. Convite válido cria/associa usuário uma única vez; token repetido, expirado ou
   revogado falha sem revelar dados internos.
2. Recuperação responde de forma indistinguível para e-mail existente ou não e
   uma redefinição válida invalida sessões anteriores.
3. Todos os oito papéis têm capacidades testadas; um tenant ou cliente não lê
   nem altera dados de outro escopo.
4. Serviços, públicos, objetivos, estratégia versionada, plano, calendário e
   preset são persistidos e auditados.
5. Upload válido fica privado e upload inválido é rejeitado antes de persistir o
   registro como disponível.
6. O mock produz prompt visual determinístico a partir do Brand Kit, preset e
   seleções do conteúdo.
7. Conteúdo referencia estratégia, pauta e preset; texto e imagem podem ser
   aprovados ou devolvidos separadamente, e uma aprovação de imagem exige mídia
   vinculada e visível por URL assinada.
8. Notificações internas continuam sendo a fonte de verdade e os e-mails podem
   ser inspecionados na caixa local.
9. Somente conteúdo aprovado/agendado recebe publicação manual; repetir a mesma
   confirmação não duplica evento.
10. Relatório do período mostra contagens reais e informa explicitamente as
    métricas indisponíveis.
11. Testes unitários, integração e E2E cobrem o caminho principal e negações de
    segurança, inclusive viewport móvel.

## Fora do escopo

- OAuth, leitura ou publicação em Instagram/Facebook;
- Meta Ads, Google Ads, orçamento ou compra de mídia;
- WhatsApp real ou aprovação por link público;
- publicação automática, scraping ou métricas simuladas;
- provider de IA pago obrigatório.
