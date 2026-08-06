# Recomendação de release — Fase IA v1

## Decisão

**NO-GO. Manter PR #4 em Draft. Não mesclar.**

## Por quê

Os três bloqueadores desta rodada (drift, rede externa em testes e armazenamento local inseguro da chave) foram corrigidos e revalidados. O NO-GO permanece porque QA-004 e QA-005 continuam altos, os contratos QA-006 seguem incompletos e a nova CI ainda precisa confirmar as correções no GitHub.

## Ordem obrigatória de correção

1. Confirmar CI integral verde para os commits corretivos.
2. Incluir gerações, feedback e snapshots na política/fluxos LGPD.
3. Persistir custo quando retornado e explicar ausência.
4. Fechar contratos de idempotência, cancelamento e aplicação de alternativa.
5. Diferenciar provider configurado de saudável e ampliar testes Hermes fake.
6. Repetir auditoria Python reproduzível e atualizar o pip da imagem worker ou aceitar formalmente o risco de build.
7. Rodar matriz manual UX/a11y e instalação independente.

## Gates para sair de Draft

- CI integral verde, inclusive E2E;
- zero rede externa nas suítes padrão mesmo com chave local presente;
- `alembic check` limpo em base e upgrade 0008;
- nenhum segredo em `.env`/filesystem inseguro; arquivo seguro ou secret manager validado;
- testes de LGPD sobre IA passando;
- auditoria de dependências repetível;
- riscos altos resolvidos ou formalmente aceitos com responsável e prazo.

## Próximo prompt recomendado

> Corrija somente QA-004 e QA-005 documentados em `docs/qa/fase-ia-v1/BUGS.md`. Defina a política LGPD para snapshots de IA antes de alterar retenção/anonimização e persista custo apenas quando o provider o retornar, sem inventar valores. Preserve isolamento multiempresa, aprovação humana, providers offline e o PR #4 em Draft. Não faça merge.
