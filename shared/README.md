# Shared

Contratos estáveis consumidos por mais de um runtime. Esta pasta não contém regras de domínio duplicadas.

- O backend é a fonte de verdade para domínio, autorização e OpenAPI.
- Tipos do frontend devem ser gerados em `shared/openapi/`, não copiados manualmente.
- Schemas de mensagens versionadas ficam em `shared/contracts/`.
- Alterar contrato exige compatibilidade, teste do produtor/consumidor e versão quando houver quebra.

