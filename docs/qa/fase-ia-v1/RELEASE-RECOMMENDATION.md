# Recomendação de release — Fase IA v1

## Decisão

**NO-GO. Manter PR #4 em Draft. Não mesclar.**

## Por quê

Há um bloqueador de CI, dois achados críticos de segurança/testes e lacunas altas de LGPD e controle de custo. Embora o produto esteja executável e os fluxos anteriores sejam sólidos, a configuração de piloto pode fazer suítes offline chamarem o provider externo.

## Ordem obrigatória de correção

1. Isolar totalmente pytest e E2E de variáveis/chaves externas.
2. Corrigir o drift das nove constraints e deixar CI verde.
3. Restringir `.env` a modo 600 e fortalecer o doctor.
4. Incluir gerações, feedback e snapshots na política/fluxos LGPD.
5. Persistir custo quando retornado e explicar ausência.
6. Fechar contratos de idempotência, cancelamento e aplicação de alternativa.
7. Diferenciar provider configurado de saudável e ampliar testes Hermes fake.
8. Rodar matriz manual UX/a11y e instalação independente.

## Gates para sair de Draft

- CI integral verde, inclusive E2E;
- zero rede externa nas suítes padrão mesmo com chave local presente;
- `alembic check` limpo em base e upgrade 0008;
- `.env` protegido;
- testes de LGPD sobre IA passando;
- auditoria de dependências repetível;
- riscos altos resolvidos ou formalmente aceitos com responsável e prazo.

## Próximo prompt recomendado

> Corrija somente os achados QA-001, QA-002 e QA-003 documentados em `docs/qa/fase-ia-v1/BUGS.md`, em commits separados. Preserve arquitetura e comportamento de produção. Garanta que `APP_ENV=test` nunca use rede externa nem chave local, alinhe as nove constraints sem editar migrations compartilhadas e proteja `.env`/doctor. Execute migrations isoladas, `make validate`, `make lint`, `make test` e `make e2e`. Não faça merge e mantenha o PR #4 em Draft.
