# Recomendação de release — Fase IA v1

## Decisão

**NO-GO. Manter PR #4 em Draft. Não mesclar.**

## Por quê

QA-001 a QA-006 estão resolvidos ou mitigados e a validação funcional local está verde. O NO-GO permanece porque a auditoria atual encontrou QA-012 alto em `js-yaml` e ainda existem gates manuais.

## Ordem obrigatória de correção

1. Corrigir ou aceitar formalmente a vulnerabilidade `js-yaml` (QA-012).
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

> Avalie exclusivamente QA-012, identifique a origem de `js-yaml` na árvore e atualize sem `--force`. Repita audit, lint, tipos, build, testes e E2E. Preserve o PR #4 em Draft e não faça merge.
