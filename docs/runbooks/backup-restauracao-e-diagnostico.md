# Runbook de diagnóstico, backup e restauração local

## Objetivo e limite

Este runbook comprova recuperação no ambiente local/piloto com dados fictícios.
Ele não substitui backup gerenciado, criptografia, cópia externa, monitoramento ou
definição formal de RPO/RTO para produção. Os scripts recusam backup sem pausa dos
processos escritores, porque banco e objetos poderiam representar instantes
diferentes.

Backups ficam em `.data/backups/`, com permissão privada, e são ignorados pelo
Git. Eles podem conter dados pessoais, hashes de senha, materiais de marca e
audit logs; não devem ser enviados por e-mail, compartilhados publicamente nem
mantidos indefinidamente.

## Diagnóstico

Com a stack iniciada, execute:

```bash
make doctor
```

O diagnóstico verifica requisitos, Compose, `.env`, portas, disco, memória,
serviços, migration atual, banco, bucket, worker, Mailpit, frontend, liveness e
readiness. Mensagens `ERRO` bloqueiam o uso; mensagens `AVISO` explicam uma
limitação que deve ser avaliada.

Os endpoints têm funções distintas:

- `/api/v1/health/live`: confirma somente que o processo da API responde;
- `/api/v1/health/ready`: confirma que a API consegue consultar o banco;
- `/api/v1/health`: alias de compatibilidade com a mesma semântica de readiness.

O worker exige `WORKER_HEARTBEAT_MAX_AGE_SECONDS` e
`WORKER_STOP_GRACE_PERIOD_SECONDS` maiores que `JOB_TIMEOUT_SECONDS`. Isso evita
marcar um job legítimo como travado e oferece tempo para o shutdown terminar o
handler atual.

## Criar um backup local

Confirme primeiro que não há operação crítica em andamento e execute:

```bash
make doctor
make backup
```

O script:

1. adquire um lock para impedir duas cópias concorrentes;
2. cria staging privado com sufixo `.partial`;
3. pausa backend e worker por alguns instantes;
4. gera dump customizado do PostgreSQL;
5. espelha o bucket privado do MinIO;
6. confirma que toda mídia referenciada no banco existe na cópia;
7. grava manifesto, log e checksums;
8. valida o dump e publica o diretório por rename atômico;
9. restaura backend/worker ao estado anterior;
10. remove somente backups antigos que já possuam marcador `VERIFIED`.

O padrão mantém sete backups locais. Para alterar a rotação:

```bash
BACKUP_RETENTION_COUNT=10 make backup
```

Não configure `BACKUP_QUIESCE=false`: o script falha fechado de propósito.

## Verificar um backup

Para verificar o mais recente:

```bash
make backup-verify
```

Para escolher uma cópia:

```bash
make backup-verify BACKUP=.data/backups/AAAAmmddTHHMMSSZ-commit
```

A verificação rejeita caminhos fora de `.data/backups`, links simbólicos,
manifesto inválido, checksum divergente, mídia ausente ou catálogo PostgreSQL
ilegível. Nunca corrija manualmente um backup que falhou; crie uma nova cópia e
investigue a origem.

## Ensaio de restauração

Execute:

```bash
make restore-test
```

Ou informe uma cópia específica com `BACKUP=...`. O ensaio cria um projeto
Docker com nome aleatório, rede interna, banco e MinIO próprios e nenhuma porta
publicada. Ele restaura os dois stores, baixa novamente os objetos, confere
checksums, referências de mídia, contagens principais, revisão Alembic e leitura
do schema pela imagem do backend. Um `trap` remove contêineres, rede, volumes e
arquivos temporários, inclusive em falha ou interrupção.

O teste nunca usa `make reset` nem os volumes da stack fonte. O nome do projeto
temporário precisa começar com `devmark-growthos-restore-`; essa proteção não
deve ser removida.

## Recuperação de falhas

### Backup interrompido

- confirme que backend e worker voltaram com `make status`;
- execute `make doctor`;
- remova somente diretórios `.partial` antigos depois de confirmar que não há
  processo de backup em andamento;
- não renomeie staging incompleto para simular sucesso.

### Checksum divergente

- trate a cópia como inválida;
- preserve o log para diagnóstico, sem publicá-lo;
- verifique disco, MinIO e PostgreSQL;
- produza um novo backup e repita `make restore-test`.

### Restore falhou

- o ambiente fonte não deve ser alterado;
- confira se o cleanup removeu o projeto com
  `docker compose ls --all`;
- consulte a primeira mensagem de erro, corrija a causa e repita;
- nunca aponte o script para um banco real ou remova a validação do prefixo.

## Produção

Antes de dados reais, definir e aprovar:

- RPO, RTO e responsável pelos testes periódicos;
- destino externo com criptografia e controle de acesso;
- política de retenção alinhada à LGPD, inclusive expiração das cópias;
- alerta de falha, trilha da execução e restauração periódica em homologação;
- procedimento específico do provedor gerenciado de PostgreSQL e storage.

O HSTS é emitido apenas quando `APP_ENV=production`; desenvolvimento local não
recebe esse header. CSP e demais headers devem ser validados novamente no domínio
e storage HTTPS definitivos antes do go-live.
