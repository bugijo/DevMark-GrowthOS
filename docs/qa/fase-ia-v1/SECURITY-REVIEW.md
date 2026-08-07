# Revisão de segurança — Fase IA v1

## Parecer

**Apta somente para piloto interno com dados fictícios.** LGPD da camada de IA, ciclo funcional e dependências altas estão corrigidos. Dados reais permanecem bloqueados por CSP, infraestrutura/segredos, validação legal e observabilidade Hermes.

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
- teste manual confirmou CSRF 403 sem token, endpoint de providers 403 para cliente, raiz privada do MinIO 403, cookie HttpOnly/SameSite=Lax e zero chave em Git, histórico, `.env` e logs;
- frontend e API entregam frame deny, nosniff, referrer/permissions policy; API usa `Cache-Control: no-store`.

## Achados

- QA-002 CRÍTICO: **resolvido**; testes recusam provider/rede externa e usam configuração offline dedicada.
- QA-003 CRÍTICO: **mitigado**; `.env` em fuseblk está sem chave, e o segredo local foi movido para arquivo Linux modo 600 validado pela aplicação.
- QA-004 ALTO: **resolvido**; snapshots seguem potencialmente identificáveis e são exportados, anonimizados e retidos por política tenant-scoped.
- QA-006 ALTO: **resolvido**; idempotência, cancelamento e aplicação exigem capability, escopo de tenant, audit log e nunca aprovam/publicam.
- QA-012 ALTO: **resolvido** em `cd7fc31`; a dependência transitiva de lint passou de `js-yaml` 4.3.0 para 4.3.1, sem override, e os audits frontend/E2E retornaram zero vulnerabilidades.
- QA-008 MÉDIO: CSP permite `unsafe-inline` em script/style.
- QA-007 MÉDIO: teste Hermes retorna indisponível, mas a listagem sem configuração persistida volta a `NOT_CHECKED`.
- `pip 25.0.1` possui seis advisories atuais; o aplicativo não executa pip nem instala entrada do usuário, mas a imagem deve ser corrigida antes de dados reais.
- HSTS não foi exigido no HTTP local; deve ser validado no terminador TLS de produção.
- Hermes configurado não significa saudável; a indisponibilidade só fica clara no uso.

## Ataques não destrutivos e limites

IDOR, escalada de papel, CSRF, enumeração, uploads e tenant crossing foram avaliados pelas suítes existentes. Não foram executados fuzzing amplo, scanner DAST externo, ataque destrutivo, exaustão real de rate limit do OpenRouter, corrupção deliberada do backup ou SSRF contra redes externas.

## Recomendação

Para o piloto, usar somente dados fictícios e acesso restrito. Antes de dados reais: remover/justificar `unsafe-inline`, corrigir pip da imagem, validar TLS/HSTS, secret manager, base legal, retenção e estado saudável do Hermes. Interromper o piloto diante de tenant crossing, segredo em log, custo inesperado ou automação de aprovação/publicação.
