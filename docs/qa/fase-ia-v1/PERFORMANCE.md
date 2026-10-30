# Desempenho — Fase IA v1

Medição local repetida em 2026-08-07, com 10 amostras aquecidas por endpoint.

| Endpoint | p50 | p95/máximo | Resposta |
|---|---:|---:|---:|
| Backend liveness | 3,3 ms | 4,8 ms | 15 B |
| Sessão autenticada/dashboard | 7,8–9,0 ms | 9,9–12,1 ms | 477 B |
| Lista de clientes | 10,4–13,5 ms | 14,5–17,9 ms | 396 B |
| Lista de conteúdos | 372,2–460,9 ms | 420,9–719,3 ms | 187.551 B |
| Comparação de versões | 33,4 ms | 37,0 ms | 2.575 B |
| Aprovações/pendências | 481,6 ms | 576,8 ms | 134.203 B |
| Exportação LGPD | 106,6 ms | 120,7 ms | 128.186 B |
| Histórico de IA | 71,2 ms | 84,6 ms | 32.476 B |
| Notificações | 24,0 ms | 37,4 ms | 49.724 B |
| Frontend | 20,9 ms | 50,9 ms | 9.433 B |
| Relatório | 32,0 ms | 75,4 ms | 925 B |

Build estático: 0,96 MiB. Memória observada: backend 97,03 MiB; frontend 104,9 MiB; worker 54,22 MiB; PostgreSQL 119,4 MiB; MinIO 277,3 MiB; Mailpit 29,62 MiB.

Geração OpenRouter real de release: 26,9 s, modelo `google/gemma-4-26b-a4b-it:free`, 3.682 tokens de entrada e 297 de saída, sem fallback. Não foi feita carga concorrente externa para evitar consumo de cota.

Achado principal: a lista de conteúdos domina latência e payload e chegou a 719,3 ms, próxima do orçamento local de 750 ms. Comparação, aprovação, exportação LGPD e histórico de IA ficaram abaixo do orçamento. Geração externa foi medida uma vez, sem carga concorrente.

Decisão: QA-009 é aceitável somente para piloto interno com base fictícia pequena. Interromper o piloto se o p95 de conteúdos ultrapassar 750 ms de forma repetida, ocorrer timeout, crescimento contínuo do payload ou impacto perceptível em 360 px.

QA-006 adicionou somente locks particionados por chave durante gerações idempotentes e
locks de linha nas mutações de cancelamento/aplicação. Não foi executada carga externa
concorrente para evitar consumo de cota; a concorrência offline com Mock passou.
