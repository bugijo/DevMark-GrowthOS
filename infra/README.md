# Infraestrutura

Este diretório reserva decisões e configurações operacionais versionadas do DevMark GrowthOS.

No ciclo atual, o ambiente local está integralmente definido em `docker-compose.yml`; não há Terraform, Kubernetes ou configuração de cloud ativa. Novos artefatos de infraestrutura só entram aqui com documentação de ambiente, rollback, segredos externos ao Git e validação correspondente na CI.
