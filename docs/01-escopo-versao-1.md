# Escopo da versão 1.0 — Clínica Piloto

## 1. Objetivo da versão

Colocar o DevMark GrowthOS em funcionamento para uma clínica veterinária e provar um processo completo de marketing assistido: configuração da marca, criação de conteúdo, revisão interna, aprovação pelo cliente, acompanhamento e auditoria.

A versão 1.0 deve ser pequena o suficiente para ser entregue e sólida o suficiente para operar. Ela não será considerada pronta se houver apenas telas demonstrativas sem backend, banco e regras reais.

## 2. Entrega do primeiro ciclo

O primeiro ciclo de implementação é o recorte vertical abaixo:

1. login por e-mail e senha;
2. organização e vínculo do usuário;
3. cadastro de uma empresa cliente;
4. Brand Kit básico;
5. criação de conteúdo por provider mock;
6. envio do conteúdo para aprovação;
7. aprovação pelo usuário cliente;
8. notificação interna para a equipe;
9. registro de todas as transições relevantes no audit log.

Esse recorte deve usar o mesmo domínio e os mesmos limites de segurança da versão completa, evitando código descartável.

## 3. Escopo funcional obrigatório

| Área | Incluído na versão 1.0 | Evidência mínima |
| --- | --- | --- |
| Acesso | Login, recuperação de senha, sessão segura, convite, organizações e papéis | Usuários da agência e do cliente entram apenas no contexto permitido |
| Clientes | Cadastro e edição de empresa, responsáveis e estado básico de onboarding | Agência cria a clínica piloto e vincula revisores |
| Marca | Brand Kit, serviços, públicos, objetivos e presets visuais | Informações persistem e são usadas como contexto da criação |
| Planejamento | Estratégia e calendário editorial | Estratégia revisável e itens posicionados em datas sugeridas |
| Conteúdo | Ideias, legendas, roteiros, prompts visuais, upload, template e modo híbrido | Conteúdo real é salvo com origem e provider identificados |
| Versões | Histórico de versões e comparação dos dados relevantes | Pedido de alteração preserva a versão anterior |
| Revisão interna | Submissão e decisão pela equipe | Só conteúdo liberado internamente chega ao cliente |
| Aprovação do cliente | Aprovar, pedir alteração, reprovar, comentar e salvar para depois | Toda decisão referencia usuário, horário e versão |
| Notificações | Caixa interna, contador, e-mail, urgência e preferências básicas | Revisor é avisado e a equipe recebe a decisão |
| Publicação | Registro manual de que um conteúdo foi publicado | Estado e data são rastreados sem publicar em rede social |
| Resultados | Relatório básico a partir de dados registrados manualmente | Resumo não inventa métricas ausentes |
| Provedores | Contratos de texto e imagem, mock obrigatório e Hermes opcional | Fluxo roda do zero sem chave paga |
| Operação | Jobs persistidos, tentativas, timeout, logs e dados de demonstração | Falha controlada pode ser consultada e repetida |
| Governança | Audit log, configuração segura e documentação | Ações relevantes são rastreáveis e segredos não estão no repositório |

## 4. Requisitos funcionais rastreáveis

### Identidade, organização e autorização

- **RF-001:** autenticar usuário ativo por e-mail e senha usando biblioteca mantida.
- **RF-002:** recuperar acesso sem revelar se um e-mail está cadastrado.
- **RF-003:** aceitar convite para uma organização e, quando aplicável, para uma empresa específica.
- **RF-004:** atribuir um dos papéis oficiais e registrar mudanças de permissão.
- **RF-005:** negar no backend qualquer leitura ou escrita fora da organização e empresa permitidas.

### Cliente e marca

- **RF-010:** permitir à agência criar e editar uma empresa cliente.
- **RF-011:** manter um Brand Kit por empresa, incluindo identidade, tom, termos, restrições, contatos e referências.
- **RF-012:** manter serviços, públicos e objetivos vinculados à empresa.
- **RF-013:** manter múltiplos presets visuais com formato, proporção, paleta, composição, regras e prompts.
- **RF-014:** armazenar logos e referências com validação de tipo/tamanho e acesso protegido.

### Estratégia e conteúdo

- **RF-020:** criar estratégia e plano editorial com origem manual ou gerada.
- **RF-021:** criar conteúdo manualmente ou por provider configurado.
- **RF-022:** oferecer provider mock determinístico e sem custo externo.
- **RF-023:** gerar ideias, legendas, roteiros e prompts visuais usando o contexto autorizado da empresa.
- **RF-024:** oferecer `TEMPLATE`, `AI_IMAGE`, `HYBRID` e `MANUAL`, ainda que o provider de IA real seja opcional.
- **RF-025:** salvar cada alteração submetida à revisão como nova versão imutável.
- **RF-026:** associar mídia a conteúdo sem confiar na IA para escrever texto final dentro da imagem.

### Aprovação, notificação e resultado

- **RF-030:** mover conteúdo por estados oficiais e validar transições no domínio.
- **RF-031:** exigir revisão interna antes de `CLIENT_REVIEW`.
- **RF-032:** permitir ao cliente decidir sobre a versão atual com comentário opcional ou obrigatório conforme a decisão.
- **RF-033:** exigir justificativa para pedido de alteração ou reprovação.
- **RF-034:** gerar nova versão depois de alterações sem sobrescrever a versão decidida.
- **RF-035:** criar notificação interna e, quando habilitado, job de e-mail.
- **RF-036:** respeitar preferências de aviso imediato, resumo diário, semanal ou somente importante.
- **RF-037:** permitir marcação manual como agendado/publicado e registrar ator e data.
- **RF-038:** produzir relatório básico somente com dados existentes.

### Auditoria e operação

- **RF-040:** registrar ator, organização, ação, recurso, data, resultado e metadados seguros de cada ação relevante.
- **RF-041:** executar trabalho assíncrono pelo worker a partir de jobs persistidos.
- **RF-042:** identificar provider, modelo/configuração, duração e resultado sem armazenar segredos em logs.
- **RF-043:** permitir uso do Hermes quando configurado e continuar operando quando indisponível.

## 5. Estados oficiais de conteúdo

Todos os módulos devem usar a mesma enumeração:

`DRAFT`, `INTERNAL_REVIEW`, `CLIENT_REVIEW`, `CHANGES_REQUESTED`, `APPROVED`, `SCHEDULED`, `PUBLISHED`, `FAILED` e `ARCHIVED`.

As transições autorizadas e a experiência de cada estado estão definidas em [Fluxos e UX](./05-fluxos-e-ux.md). `FAILED` representa falha operacional que exige diagnóstico ou nova tentativa; não substitui reprovação editorial.

## 6. Requisitos não funcionais

| Código | Requisito |
| --- | --- |
| RNF-001 | Interface mobile first, acessível, responsiva e em português do Brasil, preparada para internacionalização. |
| RNF-002 | API REST documentada por OpenAPI, com validação de entrada e erros consistentes. |
| RNF-003 | PostgreSQL com migrações reproduzíveis, chaves estrangeiras, índices e timestamps em UTC. |
| RNF-004 | Isolamento multiempresa testado em unidade, integração e fluxo de API. |
| RNF-005 | Segredos somente por ambiente/gerenciador seguro; nenhum token completo em tela ou log. |
| RNF-006 | Logs estruturados com identificador de correlação e sem conteúdo sensível desnecessário. |
| RNF-007 | Upload com lista de tipos permitidos, limite de tamanho, nome gerado e URL assinada quando aplicável. |
| RNF-008 | Jobs idempotentes quando houver efeito externo, com tentativas limitadas e timeout. |
| RNF-009 | Projeto executável localmente por Docker Compose e funcional sem API paga. |
| RNF-010 | Lint, verificação de tipos, testes e build executados no CI. |
| RNF-011 | Dependências auditadas e proteções contra injeção, XSS, abuso de login e CSRF quando aplicável. |
| RNF-012 | Documentação suficiente para instalação e operação por outra pessoa. |

## 7. Papéis incluídos

Os papéis oficiais são `SUPER_ADMIN`, `AGENCY_ADMIN`, `STRATEGIST`, `CONTENT_EDITOR`, `DESIGNER`, `CLIENT_OWNER`, `CLIENT_REVIEWER` e `VIEWER`. A matriz detalhada está em [Agentes e responsabilidades](./06-agentes-e-responsabilidades.md).

Na primeira fatia vertical, podem ser exercitados apenas os papéis necessários ao cenário (`AGENCY_ADMIN`, `CONTENT_EDITOR` e `CLIENT_REVIEWER`), mas o modelo não deve impedir os demais.

## 8. Fora da versão 1.0

Não implementar neste ciclo:

- publicação direta no Instagram, Facebook ou outra rede;
- Meta Ads ou Google Ads reais;
- criação, aumento ou gasto automático de orçamento;
- WhatsApp Business oficial;
- geração automática de vídeo;
- respostas automáticas a clientes;
- cobrança automática, planos e faturamento;
- white label, marketplace ou API pública;
- aplicativo móvel nativo;
- autonomia total de agentes;
- benchmarking entre clientes ou uso cruzado de dados;
- login por credenciais das plataformas externas.

Contratos e pontos de extensão podem ser preparados, mas não devem acionar serviços reais nem aumentar o escopo da entrega.

## 9. Critérios de aceite da versão 1.0

A versão só pode receber a marca 1.0 quando todos os itens abaixo tiverem evidência:

1. Uma agência consegue criar um cliente.
2. O cliente recebe convite.
3. O cliente entra no portal.
4. A agência cadastra o Brand Kit.
5. A agência cria um preset visual.
6. O sistema gera uma estratégia.
7. O sistema gera um calendário.
8. O sistema gera um conteúdo.
9. O sistema gera ou recebe uma imagem.
10. O conteúdo passa por revisão interna.
11. O cliente é notificado.
12. O cliente aprova ou pede alteração.
13. A alteração cria nova versão.
14. O cliente aprova a nova versão.
15. O conteúdo aparece no calendário.
16. A publicação pode ser marcada manualmente como publicada.
17. O sistema gera relatório básico.
18. O audit log registra todas as etapas.
19. Um cliente não consegue acessar dados de outro.
20. O sistema funciona no celular.
21. Os testes passam.
22. O projeto sobe por Docker Compose.
23. A documentação permite instalação por outra pessoa.
24. Nenhuma chave secreta está no repositório.
25. O sistema funciona com provider mock, mesmo sem API paga.

O documento de testes deve manter o mapeamento detalhado entre cada item, cenário automatizado ou verificação manual e sua evidência.

## 10. Definição de pronto por funcionalidade

Uma funcionalidade só está pronta quando:

- regra de domínio, API e interface do fluxo estão conectadas quando aplicável;
- autorização é validada no servidor;
- migração e seed foram atualizados quando há persistência;
- estados de carregamento, vazio, sucesso e falha foram tratados;
- eventos auditáveis foram definidos;
- testes proporcionais ao risco foram adicionados;
- lint, tipos e testes passam;
- documentação e changelog foram atualizados;
- nenhuma dependência de serviço pago foi introduzida para o caminho principal.

## 11. Restrições conhecidas da primeira entrega

- E-mails locais podem ser capturados por serviço de desenvolvimento; o canal interno continua sendo a fonte de verdade.
- Relatórios usam entrada manual até existirem conectores oficiais de métricas.
- O modo `AI_IMAGE` depende de provider opcional; template, upload e mock mantêm o fluxo testável.
- Hermes é uma otimização opcional e nunca um requisito para iniciar o produto.
- Conteúdo veterinário/saúde não pode avançar à aprovação final sem revisão profissional registrada.
