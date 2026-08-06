# Revisão UX e acessibilidade — Fase IA v1

## Resultado

Os fluxos essenciais da agência e cliente passaram nos testes automatizados WCAG 2.1 AA, e as telas críticas passaram em 360 px. A interface de IA informa provider, modelo, duração, fallback e Mock simulado, preservando aprovação humana.

## Pontos positivos

- labels, foco, navegação e ausência de overflow são verificados em fluxos essenciais;
- comparação de versões possui testes de componente;
- mensagens distinguem resposta real e simulada;
- histórico de IA é carregado pela rota do frontend;
- estados de loading e erro estão presentes no gerador;
- cliente não vê segredo nem detalhes de autenticação do provider.

## Lacunas

- não houve inspeção humana com leitor de tela;
- 768 e 1280 px não receberam comparação visual página a página;
- a jornada de “aplicar alternativa” não existe, impedindo avaliar continuidade da geração para uma versão de conteúdo;
- status “Hermes configurado” pode ser confundido com “Hermes saudável”;
- custo ausente não é explicado porque a aplicação não o captura;
- tarefas de IA compartilham um formulário genérico; não há evidência de ajuda contextual adequada para cada uma das 12 tarefas.

## Recomendação

Executar sessão manual com NVDA/Orca, teclado e zoom 200%; testar 360/768/1280 com screenshots; validar linguagem com um cliente piloto; projetar estados de provider “configurado”, “saudável”, “indisponível” e “simulado”.
