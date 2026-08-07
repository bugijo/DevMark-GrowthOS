# Revisão UX e acessibilidade — Fase IA v1

## Resultado

Os fluxos essenciais da agência e cliente passaram nos testes automatizados WCAG 2.1 AA. A rodada final também inspecionou 27 combinações de páginas em 360, 768 e 1280 px, sem overflow global ou alerta visível. A interface de IA informa provider, modelo, duração, fallback e Mock simulado, preservando aprovação humana.

## Pontos positivos

- labels, foco, navegação e ausência de overflow são verificados em fluxos essenciais;
- comparação de versões possui testes de componente;
- mensagens distinguem resposta real e simulada;
- histórico de IA é carregado pela rota do frontend;
- estados de loading e erro estão presentes no gerador;
- cliente não vê segredo nem detalhes de autenticação do provider.
- Tab e Shift+Tab percorreram navegação e controles; Enter abriu a comparação e o foco visível apresentou contorno de 3 px;
- dashboard, onboarding, planejamento, conteúdos, aprovações, privacidade, integrações e notificações foram inspecionados nos três viewports;
- o onboarding completo e os estados vazios/informativos usam linguagem compreensível;
- o Growth Agent apresenta quantidade, instrução opcional e aviso explícito de revisão humana.

## Lacunas

- Orca 46.1 existe no host, mas não houve sessão gráfica/áudio com operador humano; leitor de tela permanece sem evidência manual;
- a jornada de “aplicar alternativa” agora cria um rascunho rastreável e possui controles mobile; ainda requer inspeção humana com leitor de tela;
- status “Hermes configurado” pode ser confundido com “Hermes saudável”; após teste indisponível, configuração não persistida volta a `NOT_CHECKED`;
- custo ausente é identificado como não informado; a clareza da linguagem ainda deve ser validada com usuário piloto;
- tarefas de IA compartilham um formulário genérico; não há evidência de ajuda contextual adequada para cada uma das 12 tarefas.
- a navegação móvel é horizontal e funcional, mas alguns itens ficam fora do primeiro enquadramento e exigem rolagem deliberada.

## Recomendação

Executar sessão humana com NVDA/Orca e zoom 200%; validar linguagem com um usuário piloto; projetar estados de provider “configurado”, “saudável”, “indisponível” e “simulado”. As lacunas são aceitáveis apenas no piloto interno fictício.
