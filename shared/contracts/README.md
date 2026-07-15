# Contratos de mensagens

`worker-job-v1.schema.json` define apenas o envelope técnico. O tipo do job fica na coluna `jobs.type`; a organização fica em `jobs.organization_id` e não deve ser aceita do payload como prova de tenancy.

Dados do payload devem ser mínimos. Quando possível, guarde apenas IDs e recupere o recurso no handler após revalidar organização e estado. Nunca inclua senha, token, cookie, chave de API ou conteúdo clínico.

