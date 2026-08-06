# Recomendação de release — Fase IA v1

## Decisão

**NO-GO. Manter PR #4 em Draft. Não mesclar.**

## Por quê

QA-001 a QA-005 estão resolvidos ou mitigados, a validação local está verde e o run de CI 31094333781 passou integralmente. O NO-GO permanece porque QA-006 segue alto.

## Ordem obrigatória de correção

1. Fechar ou aceitar formalmente idempotência, cancelamento e aplicação de alternativa (QA-006).
2. Diferenciar provider configurado de saudável e ampliar testes Hermes fake.
3. Atualizar o pip da imagem worker ou aceitar formalmente o risco da ferramenta de build.
4. Rodar matriz manual UX/a11y e instalação independente.

## Gates para sair de Draft

- CI integral verde, inclusive E2E;
- zero rede externa nas suítes padrão mesmo com chave local presente;
- `alembic check` limpo em base e upgrade 0008;
- nenhum segredo em `.env`/filesystem inseguro; arquivo seguro ou secret manager validado;
- testes de LGPD sobre IA passando;
- auditoria de dependências repetível;
- riscos altos resolvidos ou formalmente aceitos com responsável e prazo.

## Próximo prompt recomendado

> Avalie exclusivamente QA-006 e defina primeiro o contrato observável de idempotência, cancelamento e aplicação de alternativa. Preserve tenant, histórico, custo, LGPD, testes offline e o PR #4 em Draft. Não faça merge.
