# Worker

Processa a tabela PostgreSQL `jobs` sem broker externo. Cada lote é reivindicado com `FOR UPDATE SKIP LOCKED`; o lease fica em `locked_at`/`locked_by`, tentativas usam backoff exponencial limitado e jobs abandonados voltam a ser elegíveis após `JOB_TIMEOUT_SECONDS`.

Handlers iniciais:

- `notification.email.console`, `EMAIL_CONSOLE` e `SEND_EMAIL`: valida o payload e registra entrega local sem enviar e-mail real;
- `provider.mock`, `PROVIDER_MOCK` e `GENERATE_CONTENT_MOCK`: resposta determinística, sem rede ou chave paga.

O contêiner instala `backend` e `worker` em modo editable e valida no início o contrato de `growthos.models.Job`. O worker não executa migrations.

Execução local, após banco migrado:

```bash
python -m pip install -e './backend[dev]' -e './worker[dev]'
python -m growthos_worker --once
pytest worker/tests
```

