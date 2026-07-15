# PROMPT MESTRE — DevMark GrowthOS

## Contexto

Você está trabalhando em um novo produto da marca **DevMark IA**.

A DevMark IA já possui um site institucional separado no repositório:

- `bugijo/DevMark-ia`

Esse repositório existente é o site público da empresa e **não deve ser transformado no sistema interno**.

O novo produto deverá ficar em um repositório separado, preferencialmente:

- `bugijo/DevMark-GrowthOS`

O site público continuará em `devmarkia.com.br`.
O sistema deverá futuramente funcionar em algo como:

- `app.devmarkia.com.br`

## Nome oficial do produto

**DevMark GrowthOS**

### Nome do orquestrador central

**Growth Agent**

### Definição do produto

O DevMark GrowthOS será uma plataforma de marketing, desenvolvimento e automação com inteligência artificial.

Ele deverá funcionar como uma central operacional para a DevMark IA e para seus clientes.

A plataforma terá agentes especializados capazes de:

- analisar empresas e perfis digitais;
- montar estratégias de marketing;
- criar calendários editoriais;
- gerar publicações;
- criar imagens;
- gerar roteiros para vídeos;
- preparar campanhas;
- organizar aprovações;
- notificar clientes;
- registrar leads e resultados;
- analisar métricas;
- sugerir melhorias;
- automatizar processos;
- integrar-se futuramente com redes sociais, Meta Ads, Google Ads, WhatsApp, e-mail, CRM e Hermes.

O primeiro cliente real será uma clínica veterinária.

O sistema deverá nascer utilizável por clínicas veterinárias e pet shops, mas sua arquitetura deve ser multiempresa e preparada para outros setores.

---

# 1. Visão final do produto

O DevMark GrowthOS deverá evoluir para um sistema operacional de crescimento digital.

O cliente não contratará apenas postagens.

Ele terá acesso a uma equipe digital formada por agentes de IA coordenados pelo Growth Agent.

## Agentes previstos na visão final

1. **Growth Agent**
   - Orquestrador central.
   - Distribui tarefas.
   - Define prioridades.
   - Controla custos.
   - Consolida resultados.
   - Decide qual agente e qual provedor usar.

2. **Audit Agent**
   - Analisa presença digital.
   - Avalia Instagram, Facebook, Google, site, WhatsApp e concorrência.
   - Gera auditoria e plano inicial.

3. **Strategy Agent**
   - Define público.
   - Posicionamento.
   - Objetivos.
   - Funil.
   - Campanhas.
   - Calendário estratégico.
   - Indicadores.

4. **Content Agent**
   - Cria ideias.
   - Legendas.
   - Carrosséis.
   - Stories.
   - Roteiros.
   - Chamadas para ação.
   - Conteúdo educativo, comercial, institucional e de relacionamento.

5. **Visual Agent**
   - Cria conceitos visuais.
   - Gera imagens por IA.
   - Aplica templates da marca.
   - Monta variações.
   - Garante proporção, logo, tipografia e identidade.

6. **Video Agent**
   - Cria roteiros.
   - Storyboards.
   - Lista de cenas.
   - Textos para narração.
   - Instruções para geração ou edição de vídeos.

7. **Ads Agent**
   - Planeja campanhas pagas.
   - Sugere orçamento.
   - Cria variações de anúncios.
   - Analisa desempenho.
   - Nunca aumenta gastos sem autorização explícita.

8. **CRM Agent**
   - Organiza leads.
   - Classifica interesses.
   - Acompanha follow-ups.
   - Recupera clientes antigos.
   - Cria campanhas segmentadas.

9. **Customer Service Agent**
   - Auxilia atendimento.
   - Sugere respostas.
   - Classifica mensagens.
   - Encaminha casos delicados.
   - Não fornece orientação médica ou veterinária sem revisão profissional.

10. **Analytics Agent**
    - Lê métricas.
    - Gera relatórios.
    - Detecta tendências.
    - Compara períodos.
    - Recomenda ações.

11. **Compliance Agent**
    - Revisa promessas.
    - Confere regras da marca.
    - Marca conteúdos de risco.
    - Exige aprovação profissional quando necessário.
    - Mantém histórico e auditoria.

12. **Development Agent**
    - Planeja landing pages.
    - Sugere integrações.
    - Gera requisitos de automação.
    - Conecta a parte de marketing à área de desenvolvimento da DevMark IA.

---

# 2. Princípios obrigatórios

O sistema deverá seguir estes princípios:

- Fácil para pessoas sem conhecimento técnico.
- Mobile first.
- Interface simples, limpa e clara.
- Poucos botões por tela.
- Linguagem humana.
- Todo item importante deve explicar o que está acontecendo.
- O cliente deve enxergar rapidamente o que precisa aprovar.
- Nenhuma publicação deve ser feita automaticamente no início sem aprovação.
- Nenhum orçamento de anúncio deve ser gasto ou aumentado sem aprovação.
- Toda ação relevante deve gerar registro de auditoria.
- O sistema deve ser multiempresa.
- Os dados de cada cliente devem ficar isolados.
- A arquitetura deve permitir trocar provedores de IA.
- O sistema não pode depender exclusivamente de uma única API.
- O Hermes poderá ser usado como motor local e orquestrador auxiliar.
- Modelos locais devem ser usados para tarefas simples e baratas.
- Modelos remotos devem ser usados quando qualidade superior for necessária.
- Nenhuma chave de API pode ser salva no código ou enviada ao GitHub.
- O sistema deve ser preparado para LGPD.
- Conteúdo veterinário ou de saúde exige revisão profissional antes da aprovação final.
- O sistema deve priorizar consistência de marca, não apenas quantidade de conteúdo.

---

# 3. Experiência do cliente

O cliente deverá entrar em um portal extremamente simples.

## Tela inicial do cliente

Mostrar:

- quantidade de itens aguardando aprovação;
- próximos conteúdos;
- calendário da semana;
- notificações;
- campanhas em andamento;
- resultados resumidos;
- mensagens da equipe;
- botão grande: **Revisar aprovações**.

## Fluxo de aprovação

Cada conteúdo deverá ter:

- preview visual;
- legenda;
- rede social;
- formato;
- data sugerida;
- objetivo;
- público;
- chamada para ação;
- observações;
- histórico de versões;
- comentários;
- botões claros:
  - Aprovar;
  - Pedir alteração;
  - Reprovar;
  - Salvar para depois.

## Status oficiais

Usar estados consistentes:

- `DRAFT`
- `INTERNAL_REVIEW`
- `CLIENT_REVIEW`
- `CHANGES_REQUESTED`
- `APPROVED`
- `SCHEDULED`
- `PUBLISHED`
- `FAILED`
- `ARCHIVED`

## Notificações

Na versão 1.0:

- notificações dentro do sistema;
- notificações por e-mail;
- contador de pendências;
- lembrete configurável;
- resumo diário opcional;
- aviso imediato para conteúdo urgente.

Futuramente:

- WhatsApp oficial;
- push;
- Telegram;
- Slack.

O usuário poderá escolher:

- aviso imediato;
- resumo diário;
- resumo semanal;
- somente notificações importantes.

---

# 4. Sistema de identidade visual

Cada cliente deverá possuir um **Brand Kit** completo.

## Dados do Brand Kit

- nome da marca;
- nome público;
- descrição;
- segmento;
- público;
- logo principal;
- logos alternativas;
- cores principais;
- cores secundárias;
- fontes;
- tom de voz;
- palavras preferidas;
- palavras proibidas;
- slogan;
- diferenciais;
- serviços;
- produtos;
- contatos;
- endereço;
- links;
- hashtags;
- chamadas para ação;
- termos obrigatórios;
- termos proibidos;
- regras jurídicas;
- restrições de imagens;
- exemplos aprovados;
- exemplos rejeitados;
- referências visuais;
- concorrentes;
- observações internas.

## Perfis visuais

Um cliente poderá ter vários presets de estilo:

- Institucional;
- Educativo;
- Promoção;
- Urgente;
- Datas comemorativas;
- Depoimento;
- Bastidores;
- Reels;
- Stories.

Cada preset deverá armazenar:

- nome;
- objetivo;
- formato;
- proporção;
- paleta;
- fontes;
- posição do logo;
- tamanho do logo;
- margens seguras;
- estilo de fundo;
- estilo fotográfico;
- nível de realismo;
- tipo de iluminação;
- composição;
- quantidade de texto;
- regras de texto;
- prompt-base;
- prompt negativo;
- imagens de referência;
- elementos permitidos;
- elementos proibidos;
- assinatura visual;
- CTA padrão.

## Regra importante para imagens

Não depender da IA para escrever textos diretamente dentro da imagem.

Fluxo preferencial:

1. A IA gera fundo, fotografia, ilustração ou elemento visual.
2. O sistema aplica textos, logo, preço e CTA com um renderizador determinístico.
3. O resultado passa por validação.
4. O cliente aprova.

Isso reduz erros de ortografia e mantém consistência visual.

## Modos de criação visual

1. `TEMPLATE`
   - Usa layout fixo da marca.
   - Mais barato.
   - Mais consistente.

2. `AI_IMAGE`
   - Gera a peça visual por IA.
   - Útil para fotografias, ilustrações e conceitos.

3. `HYBRID`
   - IA gera a imagem-base.
   - O sistema aplica layout, logo e texto.
   - Deve ser o modo recomendado.

4. `MANUAL`
   - Usuário envia imagem própria.
   - Sistema apenas aplica identidade e adapta formatos.

## Variações

Para cada conteúdo, permitir gerar:

- uma versão;
- três variações;
- variações de título;
- variações de CTA;
- variações visuais;
- adaptação para feed, story e formato vertical.

---

# 5. Quem gera cada parte

## Estratégia, auditoria e textos

O Growth Agent decide qual modelo usar.

### Camada local

Usar Hermes/Ollama para:

- classificação;
- resumo;
- organização;
- etiquetas;
- geração de rascunho;
- análise simples;
- transformação de texto;
- reaproveitamento;
- detecção de duplicidade;
- tarefas repetitivas.

### Camada remota

Usar provedor remoto configurável para:

- estratégia;
- textos finais;
- campanhas importantes;
- raciocínio complexo;
- revisão de alta qualidade;
- análise de resultados;
- conteúdos sensíveis.

Criar uma abstração de provedores.

O código não deve ficar acoplado a um único modelo.

## Imagens

Criar uma interface `ImageProvider`.

Inicialmente o sistema deve aceitar:

- provedor externo de imagem por IA;
- template local;
- upload manual.

Não fixar a arquitetura em um único serviço.

Implementar adaptadores configuráveis.

## Vídeos

Na versão 1.0:

- gerar roteiro;
- storyboard;
- lista de cenas;
- texto na tela;
- prompts para vídeo;
- instruções para gravação;
- upload do resultado.

A geração automática de vídeo entra em versão futura.

---

# 6. Arquitetura técnica recomendada

Criar um monorepo simples.

Estrutura sugerida:

```text
DevMark-GrowthOS/
├── frontend/
├── backend/
├── worker/
├── shared/
├── infra/
├── docs/
├── scripts/
├── tests/
├── .github/
├── README.md
├── AGENTS.md
├── docker-compose.yml
├── .env.example
└── LICENSE
```

## Frontend

- Next.js;
- TypeScript;
- Tailwind CSS;
- componentes acessíveis;
- design system;
- mobile first;
- interface em português do Brasil;
- preparado para internacionalização;
- painel da agência;
- portal do cliente.

## Backend

- FastAPI;
- Python;
- API REST bem documentada;
- OpenAPI;
- camada de serviços;
- camada de domínio;
- separação entre regras e infraestrutura;
- validação com schemas;
- logs estruturados;
- tratamento consistente de erros.

## Banco

- PostgreSQL;
- migrações;
- isolamento por organização;
- índices adequados;
- timestamps;
- soft delete quando necessário;
- audit log.

## Tarefas em segundo plano

Versão 1.0:

- worker simples;
- tabela de jobs;
- retries;
- timeout;
- status;
- logs.

Preparar arquitetura para Redis e fila dedicada nas versões seguintes.

## Arquivos

- armazenamento compatível com S3;
- ambiente local com MinIO ou armazenamento simples;
- produção configurável;
- URLs assinadas;
- validação de tipo e tamanho.

## Autenticação

- usar biblioteca mantida;
- não implementar criptografia ou sessão manualmente;
- e-mail e senha;
- recuperação de senha;
- papéis;
- organizações;
- convites;
- sessão segura;
- rate limiting.

## Integração com Hermes

Criar um adaptador `HermesProvider`.

O sistema deve poder funcionar sem Hermes, mas usar Hermes quando disponível.

O Hermes poderá:

- executar tarefas locais;
- rotear modelos;
- salvar memórias autorizadas;
- processar filas;
- executar agentes;
- reduzir custos.

---

# 7. Modelo inicial de dados

Criar e documentar entidades semelhantes a:

- `users`
- `organizations`
- `memberships`
- `businesses`
- `brand_profiles`
- `visual_presets`
- `audience_segments`
- `services`
- `social_profiles`
- `content_strategies`
- `content_plans`
- `content_items`
- `content_versions`
- `media_assets`
- `approvals`
- `comments`
- `notifications`
- `campaigns`
- `leads`
- `tasks`
- `jobs`
- `provider_configs`
- `prompt_templates`
- `analytics_snapshots`
- `audit_logs`

Toda entidade multiempresa deve possuir vínculo claro com a organização.

Não confiar apenas em filtros do frontend.

---

# 8. Papéis e permissões

Papéis iniciais:

- `SUPER_ADMIN`
- `AGENCY_ADMIN`
- `STRATEGIST`
- `CONTENT_EDITOR`
- `DESIGNER`
- `CLIENT_OWNER`
- `CLIENT_REVIEWER`
- `VIEWER`

Regras principais:

- Cliente enxerga somente a própria empresa.
- Revisor do cliente pode aprovar e pedir mudanças.
- Viewer apenas visualiza.
- Designer acessa visual e mídia.
- Editor acessa conteúdo.
- Agency Admin controla operação.
- Toda mudança de permissão entra no audit log.

---

# 9. Fluxo operacional

## Onboarding

1. Criar organização.
2. Cadastrar cliente.
3. Cadastrar marca.
4. Cadastrar serviços.
5. Cadastrar público.
6. Enviar logos e referências.
7. Criar presets visuais.
8. Definir tom.
9. Definir regras.
10. Definir responsáveis por aprovação.
11. Configurar notificações.
12. Gerar diagnóstico inicial.

## Planejamento mensal

1. Strategy Agent cria proposta.
2. Usuário interno revisa.
3. Cliente aprova direção.
4. Content Agent cria calendário.
5. Visual Agent cria peças.
6. Conteúdo vai para revisão interna.
7. Conteúdo vai para cliente.
8. Cliente aprova ou pede alteração.
9. Conteúdo é marcado para publicação.
10. Resultado é registrado.

## Aprendizado

O sistema deverá registrar:

- o que foi aprovado;
- o que foi rejeitado;
- pedidos de alteração;
- estilos preferidos;
- assuntos rejeitados;
- desempenho;
- comentários.

Esses dados poderão melhorar futuras sugestões.

Nunca usar dados de um cliente para treinar ou sugerir conteúdo para outro cliente sem autorização explícita.

---


# 9.1. Mapa completo de integrações externas

A arquitetura deverá possuir um **Centro de Integrações**.

Nenhuma integração deve ficar espalhada diretamente pelas regras de negócio. Cada plataforma deverá possuir um adaptador próprio, contratos claros, credenciais isoladas, logs, testes e possibilidade de funcionar em modo mock.

## Meta

Preparar conectores separados para:

- Instagram profissional;
- páginas do Facebook;
- Meta Business;
- contas de anúncio;
- Meta Ads;
- Messenger;
- WhatsApp Business Platform;
- catálogos e ativos comerciais, quando aplicável.

A implementação deverá considerar:

- autenticação oficial;
- OAuth;
- seleção de empresa, página, perfil e conta de anúncio;
- permissões e revisão do aplicativo;
- webhooks;
- renovação e expiração de tokens;
- reconexão;
- limites de API;
- histórico de sincronização;
- revogação de acesso;
- ambiente de teste;
- tratamento de falhas;
- publicação e leitura de métricas somente quando autorizado.

O sistema não poderá depender de login e senha informados manualmente pelo cliente.

## Google

Preparar conectores separados para:

- Google Ads;
- Google Business Profile;
- Google Analytics 4;
- Google Search Console;
- YouTube;
- contas gerenciadoras e contas de clientes;
- métricas, campanhas, conversões e ativos.

A implementação deverá considerar:

- OAuth;
- seleção de conta;
- contas administradoras;
- credenciais seguras;
- escopos mínimos;
- tokens renováveis;
- webhooks ou sincronização agendada;
- limites;
- logs;
- modo somente leitura;
- modo de alteração;
- aprovação antes de mudanças financeiras.

## Mensageria

Preparar conectores para:

- WhatsApp Business oficial;
- Telegram Bot;
- e-mail;
- notificações push;
- futuramente Messenger e outros canais.

Usos previstos:

- avisos de aprovação;
- resumos;
- lembretes;
- captação de leads;
- atendimento;
- follow-up;
- recuperação de clientes;
- campanhas autorizadas;
- pedidos de avaliação.

Mensagens em massa deverão respeitar consentimento, políticas da plataforma, preferências do usuário e regras de LGPD.

## Outras redes futuras

Preparar a camada de integração para receber futuramente:

- TikTok;
- LinkedIn;
- Pinterest;
- Threads;
- X;
- plataformas de e-commerce;
- CRMs;
- ERPs;
- ferramentas de agendamento.

Essas integrações não fazem parte da versão 1.0, mas a arquitetura não deve impedir sua inclusão.

## Centro de Integrações

O painel deverá exibir para cada integração:

- status;
- conta conectada;
- empresa vinculada;
- permissões concedidas;
- última sincronização;
- último erro;
- validade do token;
- botão conectar;
- botão reconectar;
- botão testar;
- botão desconectar;
- logs;
- recursos habilitados.

## Segurança das integrações

- Credenciais criptografadas em repouso.
- Segredos nunca exibidos integralmente.
- Tokens nunca enviados ao frontend sem necessidade.
- Escopos mínimos.
- Auditoria de conexão e desconexão.
- Rotação de credenciais.
- Revogação.
- Isolamento por organização.
- Proteção contra acesso cruzado.
- Tratamento de expiração.
- Retry com limites.
- Circuit breaker quando necessário.
- Idempotência para publicações e operações financeiras.

## Política de autonomia

Classificar ações externas em três níveis:

### Leitura automática

Permitida quando autorizada:

- métricas;
- comentários;
- campanhas;
- desempenho;
- perfis;
- dados públicos;
- status.

### Escrita com aprovação

Obrigatória inicialmente para:

- publicar;
- responder mensagens;
- alterar perfil;
- criar campanha;
- editar campanha;
- pausar campanha;
- alterar orçamento;
- enviar campanha em massa.

### Escrita automática controlada

Somente em versões futuras, com:

- regra explícita;
- limite financeiro;
- janela de operação;
- aprovação prévia da política;
- logs;
- possibilidade de desfazer;
- alerta imediato;
- bloqueio de emergência.

## Fases das integrações

### Versão 1.0

- Centro de Integrações;
- contratos dos providers;
- providers mock;
- configuração segura;
- notificações internas;
- e-mail;
- upload e registro manual;
- nenhuma publicação social automática;
- nenhum gasto automático.

### Versão 2.0

- Instagram;
- Facebook;
- Meta Business;
- publicação programada;
- métricas;
- Google Business Profile;
- YouTube básico;
- sincronização de perfis.

### Versão 2.5

- WhatsApp Business oficial;
- Telegram;
- CRM;
- e-mail transacional;
- atendimento e follow-up.

### Versão 3.0

- Meta Ads;
- Google Ads;
- contas gerenciadoras;
- campanhas;
- ativos;
- métricas;
- conversões;
- limites de orçamento;
- aprovação obrigatória.

### Versão 4.0

- automações controladas;
- otimização baseada em regras;
- alertas;
- ações reversíveis;
- múltiplos canais;
- políticas de autonomia por cliente.


# 10. Versões do produto

## Versão 1.0 — Clínica Piloto

Objetivo:

Colocar o sistema funcionando para a clínica veterinária e provar o fluxo completo de criação e aprovação.

### Escopo obrigatório

- autenticação;
- multiempresa;
- papéis básicos;
- cadastro de cliente;
- cadastro de marca;
- Brand Kit;
- presets visuais;
- serviços;
- público;
- objetivos;
- criação de estratégia;
- calendário editorial;
- geração de ideias;
- geração de legendas;
- geração de roteiros;
- geração de prompts visuais;
- upload de imagens;
- modo template;
- estrutura para provedor de imagem;
- modo híbrido;
- histórico de versões;
- aprovação interna;
- aprovação pelo cliente;
- comentários;
- pedidos de alteração;
- notificações internas;
- notificações por e-mail;
- painel de pendências;
- calendário;
- registro manual de publicação;
- relatório básico;
- audit log;
- configuração de provedor de IA;
- integração opcional com Hermes;
- testes;
- documentação;
- Docker Compose;
- dados de demonstração.

### Fora da versão 1.0

- publicação direta no Instagram;
- publicação direta no Facebook;
- Meta Ads real;
- Google Ads real;
- gasto automático;
- WhatsApp oficial;
- geração automática de vídeo;
- cobrança automática;
- white label;
- marketplace;
- autonomia total.

## Versão 1.1 — Operação Interna

- biblioteca de templates;
- duplicação de campanhas;
- tarefas recorrentes;
- resumo diário;
- melhorias no calendário;
- relatórios exportáveis;
- gestão de equipe;
- custos por cliente;
- dashboard da agência;
- importação de conteúdo antigo.

## Versão 2.0 — Redes Sociais

- conexão oficial com Meta;
- publicação programada;
- métricas automáticas;
- biblioteca de mídia;
- adaptação multiformato;
- acompanhamento de falhas;
- aprovação final antes da publicação.

## Versão 2.5 — CRM e Relacionamento

- leads;
- funil;
- campanhas de e-mail;
- integração com WhatsApp oficial;
- lembretes;
- recuperação de clientes;
- segmentação;
- pedido de avaliações;
- automações de relacionamento.

## Versão 3.0 — Tráfego Pago

- Meta Ads;
- Google Ads;
- criação de campanhas;
- públicos;
- criativos;
- A/B tests;
- controle de orçamento;
- alertas;
- aprovação obrigatória;
- limites de gasto;
- relatórios de conversão.

## Versão 4.0 — Autonomia Controlada

- monitoramento contínuo;
- análise de concorrentes;
- otimização de calendário;
- sugestões automáticas;
- reaproveitamento;
- agentes colaborativos;
- metas;
- orçamento de IA;
- políticas de autonomia;
- rollback;
- explicação de decisões.

## Versão 5.0 — GrowthOS Comercial

- onboarding self-service;
- cobrança;
- planos;
- white label;
- marketplace de agentes;
- marketplace de templates;
- benchmarking anonimizado;
- múltiplos idiomas;
- aplicativo móvel;
- API pública;
- parceiros;
- franquias e agências.

---

# 11. Telas obrigatórias da versão 1.0

## Agência

- Login;
- Dashboard;
- Clientes;
- Novo cliente;
- Perfil da marca;
- Brand Kit;
- Presets visuais;
- Serviços;
- Públicos;
- Estratégias;
- Calendário;
- Conteúdos;
- Editor de conteúdo;
- Mídia;
- Aprovações;
- Comentários;
- Notificações;
- Relatórios;
- Provedores de IA;
- Configurações;
- Logs.

## Cliente

- Login;
- Início;
- Pendências;
- Aprovações;
- Calendário;
- Conteúdos aprovados;
- Resultados;
- Notificações;
- Marca;
- Preferências;
- Usuários.

---

# 12. Regras de UX

- Mostrar estados vazios úteis.
- Toda tela deve explicar o próximo passo.
- Não exibir termos técnicos para o cliente.
- Manter ações principais visíveis.
- Usar confirmação para ações destrutivas.
- Permitir desfazer quando possível.
- Exibir progresso de geração.
- Exibir falhas de forma simples.
- Não deixar o usuário esperando sem feedback.
- Manter histórico.
- Permitir visualizar versão anterior.
- Toda aprovação deve registrar usuário, data e versão.
- Mostrar o número de pendências no menu.
- O portal do cliente deve funcionar muito bem no celular.
- Priorizar aprovação em poucos toques.

---

# 13. Segurança e LGPD

Implementar e documentar:

- isolamento por organização;
- controle de acesso;
- validação no backend;
- proteção de rotas;
- logs;
- rate limiting;
- upload seguro;
- segredos em ambiente;
- política de retenção;
- exportação de dados;
- exclusão;
- consentimento;
- registro de acesso;
- backups;
- recuperação;
- proteção contra injeção;
- proteção contra XSS;
- proteção contra CSRF quando aplicável;
- dependências auditadas;
- nenhuma informação clínica sensível no conteúdo de marketing;
- nenhuma orientação veterinária automática sem revisão.

---

# 14. Documentos obrigatórios antes da implementação

Criar:

```text
docs/
├── 00-visao-geral.md
├── 01-escopo-versao-1.md
├── 02-roadmap.md
├── 03-arquitetura.md
├── 04-modelo-de-dados.md
├── 05-fluxos-e-ux.md
├── 06-agentes-e-responsabilidades.md
├── 07-brand-kit-e-imagens.md
├── 08-aprovacoes-e-notificacoes.md
├── 09-integracoes-e-provedores.md
├── 10-seguranca-e-lgpd.md
├── 11-testes-e-criterios-de-aceitacao.md
├── 12-deploy-e-operacao.md
├── 13-riscos-e-limitacoes.md
└── ADR/
```

Também criar:

- `README.md`
- `AGENTS.md`
- `.env.example`
- `CONTRIBUTING.md`
- `CHANGELOG.md`

O `AGENTS.md` deve orientar agentes de programação sobre:

- arquitetura;
- padrões;
- testes;
- segurança;
- commits;
- limites;
- como executar;
- como documentar;
- como não quebrar multiempresa;
- como não expor segredos.

---

# 15. Critérios de aceitação da versão 1.0

A versão 1.0 só pode ser considerada pronta quando:

1. Uma agência consegue criar um cliente.
2. O cliente recebe convite.
3. O cliente entra no portal.
4. A agência cadastra Brand Kit.
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

---

# 16. Estratégia de implementação

## Etapa 1 — Auditoria e planejamento

Antes de escrever código:

- verificar se o repositório está vazio;
- não misturar com o site institucional;
- criar os documentos;
- criar decisões de arquitetura;
- listar riscos;
- definir o modelo de dados;
- definir fluxos;
- criar backlog;
- criar milestones.

## Etapa 2 — Fundação

- monorepo;
- frontend;
- backend;
- banco;
- migrações;
- autenticação;
- organizações;
- papéis;
- Docker;
- CI;
- lint;
- testes.

## Etapa 3 — Cliente e marca

- negócios;
- Brand Kit;
- arquivos;
- presets;
- serviços;
- públicos;
- objetivos.

## Etapa 4 — Conteúdo

- estratégia;
- calendário;
- conteúdo;
- versões;
- prompts;
- providers;
- mock provider;
- Hermes provider opcional;
- image provider abstraction.

## Etapa 5 — Aprovações

- revisão interna;
- portal do cliente;
- comentários;
- alterações;
- notificações;
- histórico;
- audit log.

## Etapa 6 — Relatórios

- registro manual;
- métricas básicas;
- resumo mensal;
- exportação simples.

## Etapa 7 — Validação

- testes unitários;
- testes de integração;
- testes end-to-end;
- acessibilidade;
- segurança;
- responsividade;
- desempenho;
- dados demo;
- documentação final.

---

# 17. Padrões de desenvolvimento

- Não criar arquivos gigantes.
- Separar domínio, serviço e infraestrutura.
- Não duplicar regras.
- Usar tipagem.
- Validar entradas.
- Tratar erros.
- Criar testes junto com funcionalidades.
- Usar migrations.
- Criar seeds.
- Criar provider mock.
- Não exigir API paga para rodar.
- Não expor segredos.
- Criar commits pequenos.
- Usar mensagens claras.
- Atualizar documentação.
- Registrar decisões relevantes em ADR.
- Não remover funcionalidade sem justificar.
- Não fazer integração real com anúncios na versão 1.0.
- Não publicar automaticamente na versão 1.0.
- Não criar promessas comerciais irreais.
- Não inventar métricas.
- Não esconder limitações.

---

# 18. Primeira execução solicitada

Execute agora a seguinte ordem:

1. Verifique o repositório.
2. Crie a estrutura inicial.
3. Crie todos os documentos obrigatórios.
4. Crie o backlog completo da versão 1.0.
5. Crie milestones.
6. Defina arquitetura e modelo de dados.
7. Defina critérios de aceite.
8. Crie `AGENTS.md`.
9. Crie `.env.example`.
10. Crie Docker Compose inicial.
11. Crie o esqueleto do frontend e backend.
12. Configure lint, testes e CI.
13. Implemente autenticação e organizações.
14. Implemente papéis e isolamento multiempresa.
15. Implemente o primeiro fluxo vertical:
    - criar cliente;
    - cadastrar marca;
    - criar conteúdo mock;
    - enviar para aprovação;
    - cliente aprovar;
    - registrar no audit log.
16. Execute os testes.
17. Documente o que foi feito.
18. Faça commits pequenos e claros.
19. Abra um pull request com resumo, riscos e próximos passos.

Não tente implementar toda a visão final de uma vez.

A prioridade é entregar uma versão 1.0 sólida, testável e fácil de usar.

---

# 19. Resultado esperado do primeiro ciclo

Ao final do primeiro ciclo deverá existir:

- documentação completa;
- arquitetura definida;
- projeto executável;
- login;
- organizações;
- cliente;
- Brand Kit básico;
- conteúdo mock;
- aprovação;
- notificação interna;
- audit log;
- testes;
- Docker;
- CI;
- README;
- pull request.

O foco é criar a fundação correta e um fluxo vertical completo.

Não criar apenas telas falsas.

Toda tela criada deve estar ligada ao backend, banco e regras reais.

---

# 20. Comunicação com o proprietário do projeto

O proprietário não é programador.

Ao concluir cada etapa:

- explique em português simples;
- diga o que foi feito;
- diga o que funciona;
- diga o que ainda não funciona;
- diga como testar;
- informe riscos;
- informe próximos passos;
- não use apenas termos técnicos;
- não peça decisões desnecessárias;
- escolha padrões seguros e documente;
- só interrompa o trabalho quando existir bloqueio real.

Comece agora pela documentação e pela fundação da versão 1.0.
