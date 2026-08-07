# Revisão de segurança — Fase IA v1

## Parecer

**LGPD da camada de IA aprovada no escopo QA-004, ciclo funcional QA-006 corrigido e QA-012 resolvido.** Exportação, anonimização e retenção incluem os novos vínculos sem remover histórico. A aprovação geral do piloto continua condicionada ao aceite dos riscos restantes e aos gates manuais.

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

- QA-002 CRÍTICO: **resolvido**; testes recusam provider/rede externa e usam configuração offline dedicada.
- QA-003 CRÍTICO: **mitigado**; `.env` em fuseblk está sem chave, e o segredo local foi movido para arquivo Linux modo 600 validado pela aplicação.
- QA-004 ALTO: **resolvido**; snapshots seguem potencialmente identificáveis e são exportados, anonimizados e retidos por política tenant-scoped.
- QA-006 ALTO: **resolvido**; idempotência, cancelamento e aplicação exigem capability, escopo de tenant, audit log e nunca aprovam/publicam.
- QA-012 ALTO: **resolvido** em `cd7fc31`; a dependência transitiva de lint passou de `js-yaml` 4.3.0 para 4.3.1, sem override, e os audits frontend/E2E retornaram zero vulnerabilidades.
- QA-008 MÉDIO: CSP permite `unsafe-inline` em script/style.
- HSTS não foi exigido no HTTP local; deve ser validado no terminador TLS de produção.
- Hermes configurado não significa saudável; a indisponibilidade só fica clara no uso.

## Ataques não destrutivos e limites

IDOR, escalada de papel, CSRF, enumeração, uploads e tenant crossing foram avaliados pelas suítes existentes. Não foram executados fuzzing amplo, scanner DAST externo, ataque destrutivo, exaustão real de rate limit do OpenRouter, corrupção deliberada do backup ou SSRF contra redes externas.

## Recomendação

Manter a matriz LGPD atualizada com o vínculo de alternativa aplicada; revalidar CSP em produção; manter a chave fora do fuseblk e preservar bloqueios de rede. Antes do piloto, concluir os gates manuais e tratar ou aceitar formalmente os riscos médios restantes.
