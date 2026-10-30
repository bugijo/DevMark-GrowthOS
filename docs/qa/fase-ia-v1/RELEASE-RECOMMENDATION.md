# Recomendação de release — Fase IA v1

## Decisão

**GO FOR CONTROLLED PILOT. Manter PR #4 em Draft até autorização explícita. Não mesclar.**

## Por quê

Não existe achado bloqueador, crítico ou alto aberto. Regressão, CI, Compose, migrações, npm audit, segurança negativa, UX em três viewports e OpenRouter real passaram. QA-007 a QA-009 são aceitos exclusivamente em ambiente interno, com dados fictícios e monitoramento. QA-010 e QA-011 ficam no backlog.

## Riscos aceitos no piloto

1. Hermes indisponível e estado `NOT_CHECKED` inconsistente; tratá-lo como desligado.
2. CSP com `unsafe-inline`; acesso restrito, sem exposição pública.
3. Lista de conteúdos próxima do orçamento; base pequena e p95 monitorado.
4. `pip 25.0.1` com seis advisories sem caminho de execução pelo app.
5. Buildx ausente e aviso Node 20 das actions v4, sem falha funcional.

## Limites obrigatórios

- somente dados fictícios e contexto demo sanitizado;
- ambiente interno, sem exposição pública, redes sociais ou e-mail real;
- revisão e aprovação humana continuam obrigatórias;
- OpenRouter sem gasto automático; Hermes considerado indisponível; Mock sempre marcado;
- interromper em tenant crossing, segredo exposto, automação indevida, custo inesperado, erro 5xx recorrente ou p95 de conteúdos acima de 750 ms.

## Bloqueios para dados reais/produção

- CAV1-23 independente continua BLOCKED;
- CSP/headers no terminador TLS, secret manager e filesystem seguro;
- correção do pip da imagem e health/modelo Hermes confiável;
- performance com volume representativo;
- base legal, contratos, retenção definitiva, e-mail transacional e profissional habilitado;
- sessão humana com leitor de tela e revisão de release.

## Próximo prompt recomendado

> Execute a validação independente CAV1-23 em clone novo, seguindo somente o README, e anexe o relatório completo ao PR #4. Não use dados reais, não retire o PR de Draft e não faça merge.
