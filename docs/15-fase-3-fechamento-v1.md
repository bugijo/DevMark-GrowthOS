# Fase 3 — fechamento da versão 1.0

**Status:** implementação concluída e gate técnico local validado na branch
`agent/fechamento-v1`; release bloqueada somente pelo aceite independente
`CAV1-23` e pela revisão/CI do Draft PR.

## Objetivo

Fechar os itens ainda abertos de `M3`, `M4`, `M6` e `M7` para tornar o DevMark
GrowthOS utilizável no piloto real de uma clínica veterinária, sem alterar a
arquitetura principal aprovada e sem ativar integrações externas proibidas.

Esta fase só poderá declarar a versão 1.0 concluída depois que produto,
segurança, operação, acessibilidade, recuperação e instalação limpa possuírem
evidência reproduzível. Código implementado sem teste, persistência, autorização
ou documentação não fecha um critério.

## Invariantes preservadas

- O sistema continua no monorepo independente `DevMark-GrowthOS`; o repositório
  institucional `DevMark-ia` permanece fora do trabalho.
- FastAPI, Next.js, PostgreSQL, worker transacional, MinIO e Mailpit permanecem
  como arquitetura principal.
- Toda entidade de negócio nova carrega `organization_id` e `business_id` quando
  aplicável; a API deriva o tenant da sessão e valida o recurso no backend.
- Provider mock continua disponível, determinístico e suficiente para executar
  a jornada sem API paga.
- Conteúdo, estratégia, decisões e revisões preservam versões imutáveis.
- Notificação interna continua sendo a fonte de verdade, mesmo quando o e-mail
  falha ou é agrupado em resumo.
- Audit log obrigatório não é apagado por solicitação comum de exclusão; quando
  necessário, referências pessoais são anonimizadas conforme política.
- Nenhuma aprovação autoriza publicação social, mensagem ou gasto externo.

## Fatias de implementação

### 1. Operação e contratos

- diagnóstico local com `make doctor`;
- backup coordenado de PostgreSQL e MinIO, checksum, verificação e restauração
  automatizada em ambiente isolado;
- rate limiting compartilhado, cadeia de proxies confiáveis e headers de
  segurança;
- liveness e readiness separadas, shutdown seguro, retenção de jobs e limites
  coerentes do worker;
- interface de antimalware, mock local, quarentena e falha fechada configurável;
- metas e medição de desempenho documentadas.

### 2. Onboarding consolidado

Assistente persistido de 15 etapas para dados da empresa, segmento, catálogos,
marca, logos, identidade visual, regras, aprovadores, notificações, preset e
revisão final. Cada etapa valida e salva no backend, pode ser retomada e não
perde dados ao navegar para trás.

### 3. Comunicação e histórico

- preferências individuais por categoria, horário e fuso;
- avisos imediatos e resumos diário/semanal idempotentes pelo worker;
- registro das tentativas de entrega;
- comparação de texto, imagem e estratégia com autores, datas, decisões,
  comentários e versão aprovada.

### 4. Providers e conformidade

- painel operacional para mock, Hermes opcional, texto, imagem, e-mail e
  armazenamento, sem devolver segredos;
- prioridade, fallback, timeout, tentativas, teste de conexão, estado e erro
  sanitizado;
- detecção determinística de conteúdo veterinário sensível combinando regras e
  provider mock;
- permissão explícita e registro de revisão profissional com justificativa;
- bloqueio do avanço enquanto a revisão obrigatória não existir.

### 5. LGPD e piloto

- consentimentos versionados, retenção configurável, exportação e solicitações
  de exclusão/anonimização;
- histórico administrativo e logs de acesso;
- telas de privacidade ligadas ao banco;
- seed fictício ampliado e roteiro manual do piloto da clínica.

### 6. Experiência e validação

- dashboard de prioridades, atalhos, breadcrumbs, filtros, paginação e estados
  vazios úteis;
- fluxo crítico acessível por teclado, leitor de tela e viewport móvel;
- comparação visual com lado a lado, alternância e zoom acessíveis;
- testes automatizados WCAG 2.1 AA nos fluxos críticos;
- instalação limpa, suíte completa, E2E mobile e matriz final de evidências.

## Evolução de dados entregue

As migrations desta fase são aditivas e sequenciais. Elas cobrem, sem
editar as revisões `0001` a `0008`:

1. `0009`: progresso de onboarding e campos ampliados da marca;
2. `0010`: preferências, entregas e resumos de notificação;
3. `0011`: sensibilidade e revisão profissional;
4. `0012`: configurações e saúde dos providers;
5. `0013`: consentimentos, finalidades, retenção e solicitações de privacidade.

O ciclo `base → 0011 → 0013 → base → 0013` e a atualização `0008 → 0013`
passaram em bancos isolados, com `alembic check` sem drift.

## Gates da Fase 3

| Gate | Evidência obrigatória |
| --- | --- |
| Onboarding | 15 etapas persistidas, retomada, validação, resumo e edição posterior |
| Notificações | preferências e resumos diário/semanal testados com Mailpit e idempotência |
| Comparação | campos, mídia e estratégia comparáveis com versão/autor/data/decisão exatos |
| Providers | mock disponível, Hermes opcional, testes seguros e nenhum segredo na API |
| Conteúdo sensível | bloqueio e revisão profissional autorizada, justificada e auditada |
| LGPD | exportação, solicitação, anonimização/retenção e histórico demonstráveis |
| Recuperação | backup verificado e restauração automatizada com dados fictícios |
| Segurança | tenancy, RBAC, sessão, CSRF, rate limit, proxy, upload e headers testados |
| Operação | doctor, health/readiness, worker, logs, limpeza e falhas recuperáveis |
| UX | fluxos críticos WCAG 2.1 AA e viewport de 360 px sem rolagem horizontal |
| Desempenho | metas, medições e correções relevantes registradas |
| Entrega | instalação limpa, migrations, lint, testes, build, E2E, CI e busca de segredos verdes |

## Fora do escopo confirmado

- Instagram, Facebook, Meta Business, Meta Ads e Google Ads reais;
- WhatsApp real;
- publicação, mensagem ou gasto automático;
- geração paga de imagem ou geração automática de vídeo;
- cobrança, white label e marketplace.

Configurações futuras podem aparecer desativadas e claramente identificadas,
mas não podem simular conexão ou sucesso externo.

## Decisão de release

Ao final da branch, a matriz de critérios indicará `PASS`, `FAIL` ou `BLOCKED`
com a respectiva evidência. A versão 1.0 só será declarada concluída se todos os
18 critérios específicos da Fase 3 e os 25 critérios `CAV1` estiverem verdes,
sem risco alto oculto. Dependências externas de go-live — infraestrutura,
contratos, base legal e profissional habilitado — continuarão explicitadas
mesmo quando o software estiver tecnicamente apto ao piloto.

A decisão e as evidências atuais estão em
[Matriz final da versão 1.0](./18-matriz-evidencias-v1.md). O software está
tecnicamente apto ao piloto local com dados fictícios, mas a versão 1.0 não deve
ser declarada concluída até outra pessoa validar `CAV1-23` e a CI do Draft PR
permanecer verde.
