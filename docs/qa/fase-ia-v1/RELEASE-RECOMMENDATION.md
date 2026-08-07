# Recomendação de release — Fase IA v1

## Decisão

**NO-GO. Manter PR #4 em Draft. Não mesclar.**

## Por quê

QA-001 a QA-006 e QA-012 estão resolvidos ou mitigados, as auditorias npm estão limpas e a CI está integralmente verde. O NO-GO permanece porque ainda existem riscos médios e gates manuais sem evidência completa.

## Ordem obrigatória de correção

1. Diferenciar provider configurado de saudável e ampliar testes Hermes fake.
2. Avaliar a CSP sem `unsafe-inline` no ambiente de produção.
3. Medir e reduzir o custo da lista de conteúdos com volume representativo.
4. Atualizar o pip da imagem worker ou aceitar formalmente o risco da ferramenta de build.
5. Rodar matriz manual UX/a11y e instalação independente.

## Gates para sair de Draft

- CI integral verde, inclusive E2E;
- zero rede externa nas suítes padrão mesmo com chave local presente;
- `alembic check` limpo em base e upgrade 0008;
- nenhum segredo em `.env`/filesystem inseguro; arquivo seguro ou secret manager validado;
- testes de LGPD sobre IA passando;
- auditoria de dependências repetível;
- riscos altos resolvidos ou formalmente aceitos com responsável e prazo.

## Próximo prompt recomendado

> Avalie exclusivamente QA-007, diferencie Hermes configurado de saudável usando providers falsos e preserve a ordem OpenRouter → Hermes → Mock. Repita as suítes offline, mantenha o PR #4 em Draft e não faça merge.
