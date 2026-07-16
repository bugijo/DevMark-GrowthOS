# Roteiro manual do piloto da clínica veterinária

**Escopo:** ambiente local, dados fictícios e provider mock. Este roteiro não
publica em rede social, não envia WhatsApp e não usa API paga.

Este é o roteiro final pretendido para o gate da versão 1.0, não uma declaração
antecipada de que todas as etapas já funcionam. Durante a Fase 3, marque como
`BLOCKED` qualquer jornada cuja pré-condição abaixo ainda não esteja integrada e
com testes verdes. A presença de um fixture no seed não substitui a regra no
backend.

| Jornada | Pré-condição do gate |
| --- | --- |
| Comparação de conteúdo, imagem e estratégia | API e interface de comparação integradas |
| Bloqueio de conteúdo sensível | classificação e revisão profissional persistidas no backend |
| Preferências, resumos e retry de notificação | migration, worker e Mailpit da Fase 3 integrados |
| Filtros da trilha de auditoria | filtros e paginação disponíveis na API e na interface |
| Datas no fuso da clínica | formatadores da interface recebem explicitamente o fuso do cliente |

## Objetivo

Validar a jornada operacional da agência e do cliente com dados persistidos:
marca, catálogos, estratégia, calendário, produção, revisão separada de texto e
imagem, pedido de alteração, registro manual de publicação, notificações e
relatório do período. O roteiro também comprova que um rascunho veterinário
sensível permanece identificável e não deve avançar sem revisão profissional.

Todas as pessoas, contatos, serviços e situações do seed são fictícios. O
endereço `vet-demo.example` usa o domínio reservado `.example` e não representa
uma clínica real.

## Pré-condições

1. Use somente o repositório `DevMark-GrowthOS` e confirme que a configuração
   local deriva de `.env.example`.
2. Execute `make doctor` e corrija itens obrigatórios antes de continuar.
3. Suba o ambiente com `make setup` e confira com `make status`.
4. Abra o portal em `http://localhost:3000` e o Mailpit em
   `http://localhost:8025`.
5. Obtenha as credenciais locais nas variáveis `DEMO_ADMIN_EMAIL`,
   `DEMO_ADMIN_PASSWORD`, `DEMO_CLIENT_EMAIL` e `DEMO_CLIENT_PASSWORD`. Não use
   credenciais de uma pessoa ou clínica real.

Se for indispensável voltar ao estado determinístico abaixo, `make reset`
apaga os volumes locais. Execute-o somente após confirmar que não há dado local
que precise ser preservado e depois rode `make setup` novamente.

## Estado inicial esperado do seed

Para o mês UTC corrente, o seed cria de forma idempotente:

| Área | Resultado esperado |
| --- | --- |
| Organização e cliente | 1 organização demo e 1 clínica veterinária fictícia |
| Equipe | 1 administrador da agência e 1 revisor do cliente, com senhas distintas |
| Onboarding | 15 etapas concluídas e editáveis, sem depender do envio de e-mail |
| Brand Kit | perfil completo, regras de linguagem, limites clínicos e contatos `.example` |
| Catálogos | 3 serviços, 3 públicos e 3 objetivos |
| Presets | 1 preset quadrado de feed e 1 preset vertical de stories |
| Estratégia | 1 estratégia mensal aprovada com 2 versões mock comparáveis |
| Calendário | 1 plano mensal/semanal e 5 pautas no mês corrente |
| Conteúdo | 5 itens e 6 versões: 1 publicado, 1 devolvido, 1 revisado em rascunho e 2 em revisão, incluindo o sensível |
| Aprovações | 10 decisões/pendências separadas entre texto e imagem |
| Mídia | 1 PNG legado e 3 imagens fictícias úteis no storage privado, incluindo antes/depois |
| Notificações | preferência imediata do administrador materializada; aprovação, alteração e revisão com categoria e urgência corretas |
| Publicação | 1 registro manual com referência `example.invalid` |

Rodar o seed novamente não deve duplicar esses registros no mesmo período.

## Jornada 1 — agência

### 1. Entrar e selecionar a clínica

1. Entre com a conta definida por `DEMO_ADMIN_EMAIL`.
2. No painel, selecione **Clínica Veterinária Demo**.
3. Navegue até **Clientes** e abra os detalhes da clínica.

Resultado esperado: a organização e a clínica vêm da sessão e do banco; não há
campo livre que conceda acesso a outra organização. O onboarding aparece como
concluído, mas pode ser reaberto para editar qualquer uma das 15 etapas.

### 2. Conferir marca e catálogos

1. Em **Marca e presets**, confira o tom “acolhedor, claro e responsável”, as
   cores, fontes, palavras proibidas e limites de comunicação clínica.
2. Confira os presets **Feed educativo acolhedor** e
   **Stories: pergunta responsável**.
3. Nos dados do cliente, confira os três serviços, públicos e objetivos.

Resultado esperado: os dois presets estão vinculados ao Brand Kit e nenhum
texto promete cura, prescreve medicamento ou oferece diagnóstico online.

### 3. Conferir estratégia e calendário

1. Em **Planejamento**, abra **Estratégia mensal demo** no mês corrente.
2. Compare as versões 1 e 2. A segunda acrescenta o pilar **Longevidade** e os
   limites para temas sensíveis. Em instalação nova, ambas preservam snapshots
   completos dos três catálogos; num upgrade legado, a versão 1 permanece como
   foi criada e a versão 2 registra o catálogo ampliado.
3. Abra **Calendário editorial demo** e alterne entre a visão mensal e semanal.
4. Confirme as cinco pautas e seus vínculos com estratégia e preset.

Resultado esperado: a estratégia aprovada é a versão 2; a versão 1 continua
disponível como histórico. A configuração de fuso da clínica permanece no
banco. Enquanto os formatadores ainda dependerem do fuso do navegador, valide
esta parte em `America/Sao_Paulo` e marque outro fuso como `BLOCKED`.

Pré-condição: a comparação de estratégia precisa estar integrada. Até isso
acontecer, valide apenas a existência persistida das duas versões e marque a
comparação visual como `BLOCKED`.

### 4. Conferir produção e histórico

Em **Conteúdos**, valide os seguintes casos:

1. **Checklist preventivo do mês** está `PUBLISHED`, com texto e imagem
   aprovados e referência de publicação manual.
2. **Como preparar o pet para a consulta** está `CHANGES_REQUESTED`: a imagem
   foi aprovada e o texto recebeu comentário de alteração.
3. **Enriquecimento ambiental em casa** está `DRAFT`, possui duas versões e
   preserva a decisão sobre a versão 1. As imagens fictícias das versões têm
   checksums distintos e permitem validar antes/depois sem dado real.
4. **Rotina responsável para pets idosos** está `CLIENT_REVIEW`, com texto e
   imagem pendentes.
5. **Sinais de alerta: quando buscar avaliação** está `CLIENT_REVIEW`, com
   decisões comuns pendentes, sem decisão profissional e sem imagem vinculada.

Resultado esperado: a comparação sempre mostra número, autor, data e a decisão
da versão correta; criar uma revisão não sobrescreve a versão anterior.

Pré-condição: API e interface de comparação precisam estar integradas. Antes
disso, a preservação pode ser conferida no banco/teste automatizado, mas esta
etapa manual permanece `BLOCKED`.

### 5. Validar o limite de conteúdo sensível

1. Abra **Sinais de alerta: quando buscar avaliação**.
2. Confirme a marca textual:
   `[RASCUNHO INTERNO — CONTEÚDO VETERINÁRIO SENSÍVEL — REVISÃO PROFISSIONAL OBRIGATÓRIA]`.
3. Confirme que o texto não contém nome de tutor, prontuário, diagnóstico, dose
   ou prescrição.
4. Com a conta cliente, tente aprovar o texto antes da decisão profissional.
5. Registre a revisão profissional com a concessão fictícia do seed e tente a
   aprovação comum novamente.

Resultado esperado no gate final: a primeira aprovação comum recebe `409` e
explica a pendência sem expor informação clínica. A decisão profissional fica
ligada à versão exata; somente depois dela a aprovação comum pode avançar. Não
remova o marcador para contornar o controle.

Pré-condição obrigatória: a classificação sensível e a revisão profissional
precisam estar implementadas no backend. Enquanto houver somente o marcador do
seed, não tente contornar o fluxo e registre esta etapa como `BLOCKED`.

## Jornada 2 — cliente

### 6. Revisar em viewport móvel

1. Saia da conta da agência e entre com `DEMO_CLIENT_EMAIL`.
2. Use uma viewport de 360 px ou um celular de teste.
3. Abra **Aprovações** e selecione **Rotina responsável para pets idosos**.
4. Navegue por teclado até texto, imagem e ações; verifique foco visível,
   rótulos e ausência de rolagem horizontal.
5. Aprove apenas um componente e confirme que o outro permanece pendente.

Resultado esperado: o cliente vê apenas sua clínica, não recebe prompts ou
notas internas e consegue tomar cada decisão em poucos toques. A decisão cria
notificação e audit log no mesmo tenant.

### 7. Solicitar uma alteração

Em um novo conteúdo de teste enviado pela agência, solicite alteração de texto
com um comentário objetivo. Não reutilize o item já semeado se for necessário
preservar as contagens determinísticas do relatório.

Resultado esperado: o conteúdo muda para `CHANGES_REQUESTED`; a versão revisada
continua preservada e uma nova correção cria outra versão, sem editar a antiga.

## Jornada 3 — operação e evidências

### 8. Conferir notificações e e-mail local

1. Volte à conta da agência e abra **Notificações**.
2. Confira os eventos de aprovação e alteração do seed.
3. Abra o Mailpit e execute as ações do fluxo que geram e-mail.
4. Aguarde o worker e confirme assunto, destinatário fictício e link local.

Resultado esperado: a notificação interna existe mesmo se o SMTP falhar; retry
não duplica entrega. Nenhum token, prompt, senha ou dado pessoal aparece em log.

Pré-condição: preferências, resumos, logs de entrega e worker agendado devem
estar integrados. As três notificações do seed comprovam categoria e urgência,
mas não comprovam sozinhas o envio ou a idempotência no Mailpit.

### 9. Conferir relatório básico

1. Em **Relatórios**, selecione do primeiro ao último dia do mês UTC corrente.
2. Antes de modificar os fixtures, confirme:
   - 5 conteúdos: 1 `PUBLISHED`, 1 `CHANGES_REQUESTED`, 2 `CLIENT_REVIEW` e 1
     `DRAFT`;
   - 6 versões e 1 revisão;
   - 1 publicação manual no canal Instagram;
   - 1 estratégia aprovada e 5 pautas de calendário;
   - métricas externas, como impressões e alcance, identificadas como
     indisponíveis.

Resultado esperado: todas as contagens vêm do banco. O produto não inventa
engajamento, conversão ou resultado de campanha.

### 10. Conferir trilha e isolamento

1. Em **Registros**, filtre as ações executadas durante o piloto.
2. Confirme ator, data, organização, clínica, recurso e versão quando aplicável.
3. Com uma conta de outra organização de teste, tente abrir diretamente os IDs
   copiados da clínica demo.

Resultado esperado: o outro tenant recebe `404` ou negação segura e não enumera
os dados. A tentativa autorizada relevante fica observável conforme a política
de audit trail.

Pré-condição: filtros e paginação da trilha precisam estar integrados. Se a
tela ainda oferecer somente a lista, valide o isolamento pela API e marque a
parte de filtro como `BLOCKED`.

### 11. Registrar publicação somente de forma manual

Use um conteúdo aprovado criado durante o piloto e registre canal, data e uma
referência fictícia. Não conecte uma conta social real.

Resultado esperado: repetir a mesma chave de idempotência não cria outra
publicação. O registro muda o estado operacional, mas não envia nada para fora
do GrowthOS.

## Encerramento

Registre para cada etapa `PASS`, `FAIL` ou `BLOCKED`, com horário, papel usado,
viewport e evidência sem dado sensível. Uma falha de isolamento, autorização,
revisão profissional, restauração ou perda de histórico impede aprovar o
piloto. Limitações de infraestrutura, base legal e disponibilidade de
profissional habilitado devem permanecer explícitas mesmo com o software verde.
