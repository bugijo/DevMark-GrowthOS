# Deploy e operação

## Objetivo

Este documento define como executar e operar a fundação da versão 1.0 de forma reproduzível. O ambiente local deve funcionar com Docker Compose e provider mock, sem conta paga. Produção exige controles adicionais e não deve reutilizar segredos ou dados de desenvolvimento.

## Topologia da versão 1.0

| Serviço | Responsabilidade | Estado persistente |
|---|---|---|
| `frontend` | Portal da agência e do cliente em Next.js. | Não. |
| `backend` | API FastAPI, autenticação, domínio e OpenAPI. | Não; persiste no banco/arquivos. |
| `worker` | Jobs, notificações e tarefas de providers. | Não; estado dos jobs fica no banco. |
| `postgres` | PostgreSQL, constraints, migrations e audit log. | Sim. |
| armazenamento local/MinIO | Ativos de mídia compatíveis com S3. | Sim, quando habilitado. |
| saída de e-mail em console | Registra entrega mock sem enviar mensagem externa. | Não. |

Na versão 1.0, a fila usa a tabela de jobs no PostgreSQL, com status, tentativas, timeout e logs. Redis e fila dedicada ficam preparados arquiteturalmente, mas não são dependências obrigatórias.

## Perfis de ambiente

### Desenvolvimento local

- `AI_PROVIDER=mock`, `IMAGE_PROVIDER=mock` e e-mail local/console;
- dados fictícios e seed de demonstração;
- e-mail simulado pelo provider de console, sem entrega externa;
- volumes Docker para banco e arquivos;
- logs legíveis, sem segredos;
- recarregamento de código apenas quando seguro para o ambiente local.

### Teste e CI

- banco e armazenamento isolados por execução;
- migrations aplicadas a partir do zero;
- provider mock determinístico;
- sem dependência de rede externa;
- sem reutilizar volumes ou credenciais de desenvolvimento;
- limpeza previsível após a suíte.

### Homologação

Deve reproduzir a configuração de produção com dados fictícios ou anonimizados. Integrações reais permanecem desabilitadas por padrão. É o ambiente para teste de migrations, rollback, responsividade e aceite antes de produção.

### Produção

- TLS obrigatório no ponto de entrada;
- `APP_ENV=production`, `SESSION_COOKIE_SECURE=true` e `SEED_DEMO_DATA=false` obrigatórios;
- segredo de autenticação aleatório, com pelo menos 32 caracteres e sem valor local/demo;
- segredos fornecidos fora da imagem;
- banco e armazenamento com backup;
- domínio, CORS, cookies e origens restritos;
- migrations controladas;
- réplicas de aplicação stateless quando necessário;
- observabilidade, alertas e retenção configurados;
- provider real ativado somente após avaliação e autorização.

O backend valida esses guardrails ao iniciar e encerra com erro seguro se a
configuração de produção reutilizar segredo local, cookie inseguro, seed demo ou um
provider de IA ainda não suportado. O provider `mock` continua permitido — e é o
único provider de IA habilitado neste ciclo — inclusive em produção. A mensagem de
erro identifica a variável inválida sem imprimir seu valor.

## Configuração

`.env.example` documenta nomes e valores não secretos. A configuração deve abranger:

- ambiente e nível de log;
- URLs públicas do frontend e backend;
- conexão do PostgreSQL;
- segredo ou chaves de autenticação;
- modo e limites dos providers;
- Hermes opcional;
- armazenamento e URLs assinadas;
- SMTP ou provider de e-mail;
- limites de upload, jobs, timeout e tentativas;
- CORS, cookies e rate limiting;
- retenção e observabilidade.

Valores obrigatórios devem ser validados ao iniciar, com erro claro e sem imprimir o valor. O modo mock não pode exigir chave paga. Segredos reais nunca entram em `.env.example`, Dockerfile, Compose versionado, imagem, log ou frontend.

## Execução local

O procedimento esperado é:

1. instalar Docker e o plugin Docker Compose;
2. copiar `.env.example` para um arquivo local ignorado pelo Git;
3. manter provider e e-mail em modo mock/local;
4. executar `docker compose up --build`;
5. aguardar health checks e migrations;
6. carregar seed de demonstração pelo comando documentado;
7. acessar frontend e API/OpenAPI pelos endereços do `README.md`; jobs de e-mail mock, quando enfileirados, aparecem nos logs do worker;
8. ao finalizar, encerrar containers sem remover volumes, salvo quando houver intenção explícita de apagar os dados locais.

O `README.md` é a referência para portas e comandos exatos. Alterações nesses comandos precisam atualizar README, Compose e CI na mesma entrega.

## Inicialização e migrations

- Migrations são versionadas e aplicadas por um processo único antes da nova aplicação receber tráfego.
- Backend e worker não devem competir para executar migration.
- A aplicação deve falhar de forma clara quando o schema for incompatível.
- Mudanças destrutivas usam estratégia expandir/migrar/contrair, com backup e plano de rollback.
- Seed é idempotente ou detecta execução anterior e usa apenas dados fictícios.
- Seed e conta demo são bloqueados em produção, inclusive quando o comando de seed é
  chamado diretamente. Em desenvolvimento, senhas e e-mails das duas identidades
  demo precisam ser distintos e as senhas devem ter ao menos 12 caracteres.

## Health checks e prontidão

- **Liveness:** processo está ativo; não depende de todos os terceiros.
- **Readiness:** aplicação consegue atender com suas dependências obrigatórias, especialmente banco.
- **Worker:** heartbeat ou métrica de última execução indica consumo de jobs.
- **Providers:** saúde separada; falha de provider opcional não derruba login ou aprovação.

Health checks não podem revelar versão sensível, credenciais, string de conexão ou detalhes internos de exceção.

## Worker e jobs

Um job registra tipo, organização, payload mínimo, status, tentativas, próxima execução, timeout, erro sanitizado e timestamps. O worker deve:

- reservar jobs de forma atômica para evitar consumo duplicado;
- validar novamente organização e recurso;
- aplicar timeout e tentativas limitadas;
- diferenciar erro transitório de erro definitivo;
- usar idempotência em notificações e qualquer escrita externa;
- enviar falhas esgotadas para estado visível e permitir repetição manual autorizada;
- encerrar com grace period, devolvendo ou concluindo a reserva com segurança.

## Observabilidade

### Logs

Logs estruturados incluem horário, serviço, ambiente, nível, correlação, organização quando apropriado, operação e resultado. Nunca incluem senha, token, cookie, chave, cabeçalho de autorização ou conteúdo pessoal desnecessário.

### Métricas iniciais

- latência, volume e erros da API;
- logins falhos e rate limiting;
- jobs pendentes, em execução, concluídos e falhos;
- idade do job mais antigo;
- notificações criadas, entregues e falhas;
- chamadas de provider, timeout e fallback;
- conexões e espaço do banco/armazenamento.

### Alertas

Alertar sobre indisponibilidade, erro elevado, fila parada, backup falho, pouco espaço, expiração de credencial e possível evento de segurança. Alertas devem ter ação clara e evitar excesso que leve a ignorá-los.

## Backup, restauração e retenção

- Banco e objetos precisam de backups coordenados e criptografados.
- Definir RPO e RTO com o proprietário antes da entrada em produção; não assumir valores não aprovados.
- Manter cópia em local separado e acesso mínimo.
- Testar restauração periodicamente em ambiente isolado.
- Documentar versão restaurada, duração, falhas e integridade verificada.
- Backups seguem retenção e exclusão LGPD; não são arquivo permanente sem finalidade.

## Deploy e rollback

1. CI valida lint, tipos, testes, migrations e build.
2. Imagens são construídas de forma reproduzível e identificadas por versão/commit.
3. Homologação recebe migration e smoke test.
4. Produção recebe backup/verificação, migration compatível e aplicação.
5. Smoke tests cobrem login, saúde, leitura autorizada e worker.
6. Falha aciona rollback da aplicação; rollback de schema só ocorre quando seguro e ensaiado.
7. Evento, responsáveis, horários e resultado ficam registrados.

Deploy não autoriza ativar publicação social, anúncios, WhatsApp ou provider pago.

## Runbooks mínimos

### Provider indisponível

Confirmar status, pausar novas chamadas se necessário, manter recursos essenciais, usar mock somente onde a política permitir e comunicar que o resultado é simulado. Não reenviar dados a outro terceiro sem autorização.

### Worker parado

Verificar heartbeat, conexão, locks e idade da fila; reiniciar com segurança; confirmar que idempotência evitou duplicidade; repetir somente jobs autorizados.

### Banco indisponível

Interromper escritas, verificar serviço e capacidade, evitar migrations concorrentes, restaurar conforme runbook e validar isolamento/integridade antes de reabrir.

### Vazamento ou credencial comprometida

Revogar/rotacionar, invalidar sessões afetadas, preservar evidências, limitar acesso, avaliar impacto e seguir o plano de incidente e comunicação aplicável.

### Falha de notificação

Manter a decisão de aprovação válida, registrar falha, apresentar alerta interno e permitir nova tentativa idempotente. Não contornar preferência do usuário com canal não autorizado.

## Critérios de aceite

1. **OPS-01:** uma instalação limpa sobe com `docker compose up --build` seguindo o README.
2. **OPS-02:** o modo local executa o fluxo vertical sem chave paga e sem entrega externa de e-mail.
3. **OPS-03:** migrations são aplicadas de forma previsível em banco vazio.
4. **OPS-04:** seed demo pode ser executado sem criar duplicidade perigosa.
5. **OPS-05:** frontend, backend, worker e banco possuem verificação de saúde adequada.
6. **OPS-06:** reiniciar worker não duplica uma notificação já processada.
7. **OPS-07:** falha de provider opcional não impede autenticação e aprovação.
8. **OPS-08:** logs correlacionam uma requisição sem expor segredo.
9. **OPS-09:** CI executa os mesmos gates essenciais disponíveis localmente.
10. **OPS-10:** imagem e configuração de produção não contêm credencial real versionada.
11. **OPS-11:** existe procedimento de backup e uma restauração pode ser comprovada antes da produção.
12. **OPS-12:** deploy possui smoke test e plano de rollback documentado.
13. **OPS-13:** jobs esgotados ficam visíveis e podem ser repetidos somente por usuário autorizado.
14. **OPS-14:** nenhuma integração ou gasto fora do escopo é ativado pelo deploy padrão.

## Fora do escopo da versão 1.0

- Kubernetes e operação multi-região;
- Redis ou fila dedicada obrigatória;
- autoscaling avançado;
- SLA comercial definido sem dados de operação;
- publicação social automática;
- Meta Ads, Google Ads e gasto automático;
- WhatsApp Business oficial;
- disaster recovery ativo-ativo.
