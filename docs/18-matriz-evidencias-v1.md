# Matriz final de evidências da versão 1.0

**Data do gate local:** 2026-08-03  
**Branch:** `agent/fechamento-v1`  
**Decisão:** tecnicamente apta ao piloto local com dados fictícios, mas a versão
1.0 ainda não pode ser declarada concluída. O aceite independente `CAV1-23` e a
CI/revisão do Draft PR permanecem pendentes.

`PASS` significa evidência reproduzida neste gate. `BLOCKED` significa que a
evidência depende de outra pessoa ou ambiente e não pode ser presumida.

## 18 gates da Fase 3

| # | Gate | Estado | Evidência |
|---:|---|---|---|
| 1 | Onboarding persistido | PASS | 15 etapas, retomada, resumo, edição e testes backend/frontend |
| 2 | Preferências de notificação | PASS | preferências por categoria, horário e fuso cobertas por testes |
| 3 | Resumos e entregas | PASS | resumos diário/semanal, idempotência, retry, worker e Mailpit |
| 4 | Comparação textual | PASS | título, legenda, CTA, objetivo e prompt visual com antes/depois |
| 5 | Comparação visual | PASS | imagem lado a lado, alternância, zoom, teclado e responsividade |
| 6 | Comparação estratégica | PASS | versões da estratégia com autor, data, comentário e decisão |
| 7 | Providers | PASS | mock obrigatório, Hermes opcional, prioridade, fallback, timeout e tentativas |
| 8 | Segredos de integração | PASS | somente nome da variável de ambiente; nenhum valor secreto retorna à API/UI |
| 9 | Conteúdo sensível | PASS | classificação determinística e bloqueio até revisão profissional auditada |
| 10 | LGPD operacional | PASS | consentimento, finalidades, retenção, exportação, solicitação e anonimização |
| 11 | Isolamento/RBAC | PASS | testes negativos entre organizações, clientes e papéis nas novas rotas |
| 12 | Migrações | PASS | `base → 0011 → 0013 → base → 0013` e `0008 → 0013`; Alembic sem drift |
| 13 | Recuperação | PASS | backup PostgreSQL/MinIO, checksums e restauração em ambiente descartável |
| 14 | Operação Compose | PASS | `make setup`, healthchecks e `make doctor`: 36 OK, 0 erro |
| 15 | Desempenho | PASS | 30 amostras com enforcement; pior p95 observado: conteúdos, 337 ms |
| 16 | Acessibilidade/móvel | PASS | Vitest e Playwright com axe, teclado e viewport de 360 px |
| 17 | Dependências e segredos | PASS | npm audit sem achados; pip-audit sem CVE conhecida; busca de padrões sem segredo |
| 18 | Entrega independente | BLOCKED | uma segunda pessoa ainda precisa executar instalação limpa usando apenas o README |

### Preparação do gate independente

O gate 18 continua `BLOCKED`, mas agora possui um pacote reproduzível para o
avaliador: seção **Validação independente CAV1-23** no README, checklist sem
conhecimento implícito, modelo em `docs/templates/cav1-23-relatorio.md` e
verificador opcional `scripts/cav1-23-check.sh`. O script registra preflight,
setup, saúde, acessos, migration, seed e E2E em `.data/cav1-23/`; ele não altera
código, não corrige falhas e termina com código não zero quando houver erro.

## 25 critérios CAV1

| Critério | Estado | Evidência principal |
|---|---|---|
| CAV1-01 | PASS | criação de cliente por API e interface |
| CAV1-02 | PASS | convite expirável, de uso único e e-mail no Mailpit |
| CAV1-03 | PASS | login do cliente e sessão segura no portal |
| CAV1-04 | PASS | Brand Kit persistido e isolado por empresa |
| CAV1-05 | PASS | preset visual persistido, autorizado e associado |
| CAV1-06 | PASS | estratégia versionada gerada com mock |
| CAV1-07 | PASS | plano e calendário editorial persistidos |
| CAV1-08 | PASS | conteúdo mock persistido sem API paga |
| CAV1-09 | PASS | upload/geração visual, mídia privada e URL curta assinada |
| CAV1-10 | PASS | revisão interna e máquina de estados centralizada |
| CAV1-11 | PASS | notificação interna e entrega local ao cliente correto |
| CAV1-12 | PASS | aprovação ou pedido de alteração por versão atual |
| CAV1-13 | PASS | correção cria nova versão e preserva histórico |
| CAV1-14 | PASS | nova versão recebe decisão independente e auditada |
| CAV1-15 | PASS | conteúdo aprovado aparece no calendário |
| CAV1-16 | PASS | publicação manual idempotente e sem rede social |
| CAV1-17 | PASS | relatório usa somente dados persistidos e explicita ausências |
| CAV1-18 | PASS | audit log contém ator, tenant, recurso e ação relevante |
| CAV1-19 | PASS | matriz negativa multiempresa para API, mídia, relatórios e novos módulos |
| CAV1-20 | PASS | fluxo crítico e comparações responsivos e acessíveis em celular |
| CAV1-21 | PASS | gate local completo registrado abaixo |
| CAV1-22 | PASS | Compose construído, migrado, semeado e saudável |
| CAV1-23 | BLOCKED | requer execução por pessoa que não implementou o sistema |
| CAV1-24 | PASS | `.env` ignorado e busca em arquivos rastreados sem padrão de chave privada |
| CAV1-25 | PASS | mock determinístico cobre o fluxo sem provider pago ou rede externa obrigatória |

## Evidência técnica do gate

- Backend: 209 testes aprovados; existe 1 aviso de depreciação do adaptador
  `httpx` usado por `starlette.testclient`, sem falha funcional.
- Worker: 41 testes aprovados.
- Frontend: 52 testes aprovados.
- E2E: 9 cenários aprovados, incluindo 2 verificações automatizadas WCAG 2.1 AA.
- `make validate`, `make lint`, `make test`, `make e2e`, build do Next.js,
  `npm audit --audit-level=high` e `git diff --check` executados no fechamento.
- `pip-audit`: nenhuma vulnerabilidade conhecida nas dependências instaladas;
  `devmark-growthos-backend` e `growthos-worker` são pacotes locais sem registro
  no PyPI e, por isso, foram corretamente ignorados pelo scanner.
- O Python 3.12 deste host não possui `ensurepip`; o scanner foi instalado em
  diretório temporário usando o pip do `.venv`, sem alterar dependências do projeto.

## Bloqueios e riscos residuais

1. `CAV1-23`: atribuir a uma segunda pessoa a instalação limpa e guardar a
   evidência (máquina, commit, comandos e resultado) usando o modelo publicado.
2. O volume `fuseblk` deste host mantém `.env` em modo `777` mesmo após
   `chmod 600`; não usar dados reais nesse volume. Produção/homologação exige
   filesystem Linux ou secret manager que preserve acesso restrito.
3. Base legal, contratos, retenção definitiva, infraestrutura, e-mail
   transacional e profissional habilitado são dependências de go-live, não
   resultados que o software possa autoaprovar.
4. A CI remota precisa permanecer verde no Draft PR antes da decisão humana de release.

## Como fechar a decisão de release

Uma pessoa que não participou da implementação deve clonar a branch em ambiente
limpo, seguir apenas o README, executar `make setup`, `make status`, o roteiro
manual e `make e2e`, e anexar ao PR o relatório preenchido. Com `CAV1-23` em
`PASS`, CI verde e revisão aprovada, a matriz poderá declarar os 43 itens verdes
e liberar a versão 1.0 sem ativar qualquer integração externa fora do escopo.
