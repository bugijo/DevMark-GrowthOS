# Infraestrutura

Este diretório registra complementos operacionais do DevMark GrowthOS. A
topologia local executável permanece definida no `docker-compose.yml` da raiz,
para que `make setup` e a CI usem exatamente o mesmo contrato.

Não coloque segredos, volumes, dumps ou arquivos `.env` aqui. Manifestações de
homologação/produção só devem ser adicionadas quando houver ambiente e processo
de deploy aprovados; elas não podem ativar publicação social, anúncios ou
WhatsApp real por padrão.
