# Medição e metas de desempenho

## Como medir

Com a stack saudável e o seed fictício aplicado, execute:

```bash
make performance
```

O comando autentica uma única vez com a conta demo, aquece cada rota e mede
latência `p50`, `p95`, maior amostra e tamanho da resposta. Também informa o
tamanho dos arquivos estáticos já construídos e a memória observada pelo
Docker. Senha, cookie e corpo de conteúdo não são impressos nem gravados.

Para repetir um gate local mais rigoroso:

```bash
make performance PERFORMANCE_ARGS="--iterations 30 --enforce"
```

O resultado depende do hardware e não substitui teste de carga. Registre data,
commit, quantidade de fixtures e recursos da máquina ao comparar execuções.

## Metas da versão 1.0

| Indicador | Meta piloto | Ação quando exceder |
| --- | --- | --- |
| Liveness aquecido | `p95 <= 200 ms` local | verificar runtime, proxy e saturação |
| GET autenticado com até 50 itens | `p95 <= 750 ms` local | analisar query, N+1, índice e payload |
| Fluxo crítico no navegador | LCP `<= 2,5 s` em produção | dividir bundle, cachear estáticos e otimizar imagens |
| Mudança visual | CLS `<= 0,1` | reservar dimensões e evitar conteúdo tardio |
| Interação | INP `<= 200 ms` | reduzir trabalho síncrono e renderizações |
| Imagem de mídia | miniatura apropriada e carregamento tardio | não servir original grande em listas |
| Memória | sem crescimento contínuo em 30 min de piloto | revisar retenção, streams e jobs |

As metas de Web Vitals seguem o percentil 75 dos acessos reais; o script local
mede tempo HTTP e não deve ser apresentado como Web Vitals.

## Diagnóstico de rotas e queries

- Os logs estruturados do backend incluem `request_id`, rota, status e duração,
  sem query string, cookie ou corpo. Ordene os eventos por `duration_ms` para
  localizar rotas lentas.
- Listagens devem limitar ou paginar resultados e preservar filtros no backend.
- Toda consulta de negócio continua filtrada por organização e empresa; uma
  otimização nunca pode remover esse predicado.
- Use `EXPLAIN (ANALYZE, BUFFERS)` somente com dados fictícios e fora da
  transação do usuário. Não registre parâmetros pessoais.
- Compare `docker stats --no-stream` antes e depois de E2E ou lote do worker.

## Evidência de release

Antes de fechar a versão 1.0, este runbook deve receber uma tabela com os
resultados medidos no commit candidato, o bundle produzido por `npm run build`,
os endpoints acima da meta e as correções ou limitações aceitas. Uma medição
sem hardware/commit identificados não fecha o gate de desempenho.
