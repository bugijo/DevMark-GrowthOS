# Desempenho — Fase IA v1

Medição local em 2026-08-05, 10 amostras aquecidas por endpoint.

| Endpoint | p50 | p95/máximo | Resposta |
|---|---:|---:|---:|
| Backend liveness | 8,3 ms | 12,6 ms | 15 B |
| Sessão autenticada | 13,1 ms | 18,2 ms | 477 B |
| Lista de clientes | 12,7 ms | 13,8 ms | 396 B |
| Lista de conteúdos | 329,4 ms | 410,3 ms | 135.082 B |
| Notificações | 19,4 ms | 26,1 ms | 38.235 B |
| Frontend | 11,1 ms | 13,5 ms | 9.433 B |
| Relatório | 30,8 ms | 34,1 ms | 839 B |

Build estático: 0,95 MiB. Memória: backend 103,7 MiB; frontend 98,57 MiB; worker 52,62 MiB; PostgreSQL 82,81 MiB; MinIO 272,7 MiB; Mailpit 27,19 MiB.

Geração OpenRouter real observada anteriormente: 2.499 tokens de entrada, 1.345 de saída; o teste backend contaminado levou aproximadamente 46 s. Não foi feita carga concorrente externa para evitar consumo de cota.

Achado principal: a lista de conteúdos domina latência e payload. Medições específicas de comparação, aprovação, exportação LGPD e IA em série permanecem pendentes.
