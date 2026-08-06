# Revisão de segurança — Fase IA v1

## Parecer

**Não aprovado para dados reais.** O isolamento multiempresa, autorização, CSRF, cookies, uploads e URLs privadas possuem boa cobertura automatizada. Os bloqueios são operacionais e de privacidade da nova camada de IA.

## Evidências positivas

- zero padrões de chave em arquivos rastreados, histórico e logs;
- `.env` ignorado pelo Git;
- chave não aparece no frontend nem no banco;
- contexto externo limitado a marca, serviços, públicos, objetivos e planejamento;
- testes negativos de tenant, cliente, papéis, mídia e endpoints administrativos;
- CSRF e cookies de sessão exercitados;
- headers: frame deny, nosniff, referrer policy, permissions policy, COOP/CORP e cache no-store da API;
- Mock permanece disponível e respostas simuladas são identificadas;
- conteúdo sensível exige revisão e não há publicação/aprovação automática.

## Achados

- QA-002 CRÍTICO: testes podem transmitir contexto ao OpenRouter real.
- QA-003 CRÍTICO: `.env` modo 777.
- QA-004 ALTO: LGPD não inclui entidades/snapshots de IA.
- QA-008 MÉDIO: CSP permite `unsafe-inline` em script/style.
- HSTS não foi exigido no HTTP local; deve ser validado no terminador TLS de produção.
- Hermes configurado não significa saudável; a indisponibilidade só fica clara no uso.

## Ataques não destrutivos e limites

IDOR, escalada de papel, CSRF, enumeração, uploads e tenant crossing foram avaliados pelas suítes existentes. Não foram executados fuzzing amplo, scanner DAST externo, ataque destrutivo, exaustão real de rate limit do OpenRouter, corrupção deliberada do backup ou SSRF contra redes externas.

## Recomendação

Bloquear chamadas externas em qualquer `APP_ENV=test`; proteger `.env`; ampliar LGPD para IA; revalidar CSP em produção; adicionar teste canário que falha se qualquer socket externo for aberto durante pytest/E2E.
