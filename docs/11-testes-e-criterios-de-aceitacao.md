# Testes e critérios de aceitação

## Estratégia

Testes devem comprovar regras reais do backend, banco, worker e frontend. Telas isoladas com dados fixos não são suficientes. O fluxo vertical mínimo precisa atravessar login, organização, cliente, Brand Kit, geração mock, aprovação, notificação e audit log.

Prioridades:

1. isolamento entre organizações e permissões;
2. integridade do fluxo e das versões aprovadas;
3. funcionamento sem API paga;
4. segurança de autenticação, entrada e segredos;
5. experiência móvel e acessível;
6. confiabilidade de jobs e notificações;
7. instalação reproduzível por Docker Compose.

## Camadas de teste

### Unitários

Cobrem regras de domínio sem rede ou banco quando possível:

- transições de status;
- matriz de papéis e permissões;
- validação do Brand Kit;
- criação de versões;
- seleção e fallback de provider;
- política de autonomia;
- idempotência e regras de notificação.

### Integração

Executam serviços com banco e componentes reais do projeto:

- autenticação e memberships;
- filtros obrigatórios de organização;
- persistência, migrations e constraints;
- criação de audit log e outbox/jobs;
- API com provider mock;
- worker, retries e falhas controladas;
- armazenamento local ou compatível com S3.

### Contrato

Cada adaptador deve passar pelo mesmo conjunto de casos do contrato:

- resposta válida;
- entrada inválida;
- timeout;
- indisponibilidade;
- erro de autenticação;
- resposta incompatível;
- cancelamento ou limite excedido.

Na versão 1.0, providers externos reais não são requisito de CI. O mock valida os contratos sem rede.

### Ponta a ponta

O cenário principal usa frontend, API e banco:

1. usuário da agência entra;
2. cria organização/cliente e Brand Kit;
3. cria conteúdo com provider mock;
4. envia para revisão e depois para o cliente;
5. cliente autenticado recebe a pendência;
6. cliente aprova ou pede alteração;
7. sistema cria notificação e audit log;
8. tentativa de outro cliente acessar o item é negada.

Manter ao menos um caminho de sucesso e caminhos de alteração, acesso negado e repetição idempotente.

### Frontend, acessibilidade e responsividade

- Testes de componentes para estados vazio, carregando, sucesso, erro e sem permissão.
- Navegação por teclado, foco visível, nomes acessíveis e contraste adequado.
- Aprovação em viewport de celular sem rolagem lateral e com ação principal clara.
- Linguagem em português simples e mensagens que expliquem o próximo passo.
- O cliente não deve depender de termo técnico para concluir uma aprovação.

### Segurança

- Matriz negativa de acesso entre organizações, empresas e papéis.
- Manipulação de IDs, paginação, filtros, exportação e arquivos.
- Rate limiting nas rotas sensíveis.
- Upload inválido e URL expirada.
- Injeção, XSS e CSRF quando aplicável.
- Busca automática por segredos e auditoria de dependências.
- Redação de dados sensíveis em logs e erros.

## Dados e ambiente de teste

- Fixtures possuem duas ou mais organizações para detectar vazamento cruzado.
- Cada organização tem usuários internos/cliente, empresa, Brand Kit e conteúdo distintos.
- Relógio, UUIDs e aleatoriedade são controlados nos testes que exigem determinismo.
- Provider mock é o padrão e não acessa internet.
- Testes não usam chaves reais nem contas pessoais.
- Migrations são aplicadas do zero e também sobre a versão anterior suportada.
- Dados demo são reconhecíveis como fictícios e não representam métricas reais.

## Gates de qualidade

Antes de integrar uma etapa:

1. formatação e lint do frontend, backend e worker passam;
2. verificação de tipos passa;
3. testes unitários e de integração passam;
4. cenário ponta a ponta relevante passa;
5. migrations sobem em banco limpo;
6. build de produção e imagens Docker concluem;
7. scanner de segredos não encontra credencial;
8. documentação e `.env.example` refletem a mudança.

Os comandos exatos devem permanecer centralizados no `README.md` e na configuração do monorepo. A CI deve executar os mesmos comandos disponíveis localmente.

## Critérios de aceitação da versão 1.0

A versão 1.0 só pode ser declarada pronta quando todos os itens abaixo tiverem evidência reproduzível:

1. **V1-01:** uma agência consegue criar um cliente.
2. **V1-02:** o cliente recebe convite válido e de uso único.
3. **V1-03:** o cliente entra no portal com sessão segura.
4. **V1-04:** a agência cadastra o Brand Kit da empresa.
5. **V1-05:** a agência cria e associa um preset visual.
6. **V1-06:** o sistema gera uma estratégia, com provider mock quando não há API paga.
7. **V1-07:** o sistema gera um calendário editorial.
8. **V1-08:** o sistema gera um conteúdo ligado à empresa correta.
9. **V1-09:** o sistema gera ou recebe uma imagem válida.
10. **V1-10:** o conteúdo passa por revisão interna.
11. **V1-11:** o cliente correto é notificado.
12. **V1-12:** o cliente aprova ou pede alteração da versão atual.
13. **V1-13:** a correção após o pedido de alteração cria nova versão e preserva a anterior.
14. **V1-14:** o cliente aprova a nova versão.
15. **V1-15:** o conteúdo aprovado aparece no calendário.
16. **V1-16:** um usuário autorizado marca manualmente o conteúdo como publicado.
17. **V1-17:** o sistema gera relatório básico sem inventar métricas.
18. **V1-18:** o audit log registra todas as etapas relevantes com autor e organização.
19. **V1-19:** um cliente não acessa dados de outro, inclusive por API direta e IDs manipulados.
20. **V1-20:** o portal e o fluxo de aprovação funcionam em celular.
21. **V1-21:** toda a suíte automatizada passa no ambiente documentado.
22. **V1-22:** o projeto sobe por Docker Compose a partir de uma instalação limpa.
23. **V1-23:** outra pessoa consegue instalar e executar seguindo apenas a documentação.
24. **V1-24:** nenhuma chave secreta está no repositório ou nas imagens publicadas.
25. **V1-25:** o fluxo funciona com provider mock, sem API paga e sem acesso externo obrigatório.

## Critérios do primeiro fluxo vertical

Antes de ampliar módulos, o primeiro ciclo deve demonstrar:

1. **FV-01:** login válido e bloqueio de credencial inválida.
2. **FV-02:** criação de organização e associação do usuário autorizado.
3. **FV-03:** cadastro de cliente isolado por organização.
4. **FV-04:** cadastro e leitura de Brand Kit básico.
5. **FV-05:** criação determinística de conteúdo mock.
6. **FV-06:** envio do conteúdo para revisão interna e cliente usando transições válidas.
7. **FV-07:** aprovação pelo usuário cliente autorizado.
8. **FV-08:** notificação interna visível apenas ao destinatário correto.
9. **FV-09:** audit log cobre criação, envio e decisão.
10. **FV-10:** teste negativo comprova isolamento entre pelo menos duas organizações.

## Evidência e rastreabilidade

Cada critério deve apontar para um ou mais testes, procedimento manual ou artefato de CI. Falha conhecida não pode ser escondida: deve ter risco, impacto, responsável e decisão de bloqueio ou adiamento.

Uma etapa está concluída quando código, migrations, testes, documentação e observabilidade correspondentes estão integrados. Cobertura percentual isolada não substitui cenários críticos; a meta numérica será definida após a linha de base.

## Fora do escopo de validação da versão 1.0

- publicação real em redes sociais;
- Meta Ads, Google Ads ou gasto financeiro;
- WhatsApp Business oficial;
- geração automática de vídeo;
- testes com credenciais pessoais ou produção de clientes;
- garantia de disponibilidade ou qualidade de um provider externo desativado;
- autonomia de escrita sem aprovação humana.
