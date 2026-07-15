# Histórico de mudanças

Todas as mudanças relevantes do DevMark GrowthOS serão registradas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/). Enquanto a versão 1.0 não for publicada, mudanças entram em **Não lançado**.

## [Não lançado]

### Adicionado

- documentação inicial de visão, escopo, arquitetura, dados, fluxos, providers, segurança, testes, operação e riscos da versão 1.0;
- regras de contribuição e orientação para agentes de programação;
- backlog priorizado e milestones executáveis para a clínica piloto;
- contrato inicial de configuração local sem segredos e com providers mock;
- fundação planejada do monorepo com frontend, backend, worker, testes e Docker Compose;
- definição do primeiro fluxo vertical: login, organização, cliente, Brand Kit, conteúdo mock, aprovação, notificação interna e audit log.

### Segurança

- isolamento multiempresa e autorização no backend definidos como requisitos bloqueantes;
- proibição de segredos no repositório e de uso cruzado de dados entre clientes;
- revisão profissional obrigatória para conteúdo veterinário ou de saúde.

### Limites conhecidos

- a versão 1.0 não publica automaticamente em redes sociais;
- Meta Ads, Google Ads, WhatsApp oficial e gasto automático permanecem fora do escopo;
- providers externos e Hermes são opcionais; o funcionamento local depende apenas do provider mock.

<!-- Ao criar uma versão, mova os itens de "Não lançado" para uma seção como:
## [0.1.0] - AAAA-MM-DD
Use apenas mudanças verificadas e não antecipe funcionalidades ainda não entregues.
-->
