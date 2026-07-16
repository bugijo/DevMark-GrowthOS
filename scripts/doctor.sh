#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

checks_ok=0
checks_warning=0
checks_failed=0

ok() {
  checks_ok=$((checks_ok + 1))
  printf 'OK     %s\n' "$1"
}

warning() {
  checks_warning=$((checks_warning + 1))
  printf 'AVISO  %s\n' "$1"
}

failed() {
  checks_failed=$((checks_failed + 1))
  printf 'ERRO   %s\n' "$1"
}

env_value() {
  local key="${1:?variável obrigatória}"
  local fallback="${2-}"
  local value
  value="$(sed -n "s/^${key}=//p" .env 2>/dev/null | tail -n 1 | tr -d '\r')"
  printf '%s\n' "${value:-$fallback}"
}

positive_integer() {
  [[ "${1-}" =~ ^[1-9][0-9]*$ ]]
}

container_health() {
  local container_id="${1:?container obrigatório}"
  docker inspect \
    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
    "$container_id" 2>/dev/null
}

port_is_listening() {
  local port="${1:?porta obrigatória}"
  command -v ss >/dev/null 2>&1 || return 2
  ss -H -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${port}$"
}

check_command() {
  local command_name="${1:?comando obrigatório}"
  local help_text="${2:?orientação obrigatória}"
  if command -v "$command_name" >/dev/null 2>&1; then
    ok "$command_name está disponível."
  else
    failed "$command_name não foi encontrado. $help_text"
  fi
}

printf 'Diagnóstico do DevMark GrowthOS\n'
printf 'Diretório: %s\n\n' "$ROOT_DIR"

check_command docker "Instale Docker Engine 24 ou superior."
check_command curl "Instale curl e execute novamente."
check_command git "Instale Git e execute novamente."
check_command sha256sum "Instale GNU coreutils e execute novamente."
check_command realpath "Instale GNU coreutils e execute novamente."

docker_ready=false
compose_ready=false
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    docker_ready=true
    docker_version="$(docker version --format '{{.Server.Version}}' 2>/dev/null || true)"
    ok "Docker está acessível${docker_version:+ (servidor $docker_version)}."
  else
    failed "O Docker está instalado, mas o daemon não está acessível. Inicie o serviço Docker."
  fi
  if docker compose version >/dev/null 2>&1; then
    compose_ready=true
    compose_version="$(docker compose version --short 2>/dev/null || true)"
    ok "Docker Compose v2 está disponível${compose_version:+ ($compose_version)}."
  else
    failed "Docker Compose v2 não está disponível. Instale o plugin docker compose."
  fi
fi

if [[ -f .env ]]; then
  ok "O arquivo .env local existe."
  env_mode="$(stat -c '%a' .env 2>/dev/null || true)"
  if [[ "$env_mode" =~ ^[0-7]{3,4}$ ]] && ((8#$env_mode & 077)); then
    warning "O arquivo .env permite acesso de grupo/outros (modo $env_mode). Rode chmod 600 .env."
  elif [[ -n "$env_mode" ]]; then
    ok "O arquivo .env possui permissões privadas (modo $env_mode)."
  else
    warning "Não foi possível confirmar as permissões do arquivo .env."
  fi
  if git check-ignore -q .env 2>/dev/null; then
    ok "O arquivo .env está ignorado pelo Git."
  else
    failed "O arquivo .env não está ignorado pelo Git. Não faça commit de credenciais."
  fi
else
  failed "O arquivo .env ainda não existe. Rode make setup para criá-lo com valores locais."
fi

if [[ "$compose_ready" == "true" && -f .env ]]; then
  if docker compose config --quiet >/dev/null 2>&1; then
    ok "A configuração do Docker Compose é válida."
  else
    failed "A configuração do Compose é inválida. Confira .env e docker-compose.yml."
  fi
fi

available_mb="$(df -Pm "$ROOT_DIR" 2>/dev/null | awk 'NR == 2 {print $4}')"
minimum_disk_mb="${DOCTOR_MIN_DISK_MB:-2048}"
if positive_integer "$available_mb" && positive_integer "$minimum_disk_mb"; then
  if ((available_mb >= minimum_disk_mb)); then
    ok "Há ${available_mb} MiB livres no disco do projeto."
  else
    failed "Há somente ${available_mb} MiB livres. Libere ao menos ${minimum_disk_mb} MiB."
  fi
else
  warning "Não foi possível medir o espaço livre em disco."
fi

memory_mb="$(awk '/MemTotal:/ {printf "%d", $2 / 1024}' /proc/meminfo 2>/dev/null || true)"
minimum_memory_mb="${DOCTOR_MIN_MEMORY_MB:-2048}"
if positive_integer "$memory_mb" && positive_integer "$minimum_memory_mb"; then
  if ((memory_mb >= minimum_memory_mb)); then
    ok "A máquina possui ${memory_mb} MiB de memória total."
  else
    warning "A máquina possui ${memory_mb} MiB de memória; recomenda-se ao menos ${minimum_memory_mb} MiB."
  fi
else
  warning "Não foi possível medir a memória total."
fi

if command -v python3 >/dev/null 2>&1; then
  python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [[ "$python_version" == "3.12" ]]; then
    ok "Python 3.12 está disponível para testes no host."
  else
    warning "Python do host é ${python_version:-desconhecido}; make install requer Python 3.12."
  fi
else
  warning "Python 3.12 não foi encontrado; a stack Docker ainda pode funcionar."
fi
if command -v node >/dev/null 2>&1; then
  node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || true)"
  if [[ "$node_major" == "22" ]]; then
    ok "Node.js 22 está disponível para testes no host."
  else
    warning "Node.js do host é major ${node_major:-desconhecida}; make install requer Node.js 22."
  fi
else
  warning "Node.js 22 não foi encontrado; a stack Docker ainda pode funcionar."
fi

if [[ "$docker_ready" == "true" && "$compose_ready" == "true" ]]; then
  declare -A service_containers=()
  for service in postgres minio mailpit backend worker frontend; do
    container_id="$(docker compose ps -q "$service" 2>/dev/null || true)"
    service_containers[$service]="$container_id"
    if [[ -z "$container_id" ]]; then
      failed "O serviço $service não está em execução. Rode make setup."
      continue
    fi
    health="$(container_health "$container_id")"
    if [[ "$health" == "healthy" ]]; then
      ok "O serviço $service está saudável."
    else
      failed "O serviço $service está no estado $health. Consulte make logs."
    fi
  done

  init_id="$(docker compose ps -a -q minio-init 2>/dev/null || true)"
  if [[ -n "$init_id" && "$(docker inspect --format '{{.State.ExitCode}}' "$init_id" 2>/dev/null)" == "0" ]]; then
    ok "A inicialização do bucket MinIO terminou com sucesso."
  else
    failed "A inicialização do bucket MinIO não terminou com sucesso. Rode make setup."
  fi

  declare -A port_services=(
    ["$(env_value FRONTEND_PORT 3000)"]=frontend
    ["$(env_value BACKEND_PORT 8000)"]=backend
    ["$(env_value POSTGRES_PORT 5432)"]=postgres
    ["$(env_value MINIO_API_PORT 9000)"]=minio
    ["$(env_value MINIO_CONSOLE_PORT 9001)"]=minio
    ["$(env_value MAILPIT_SMTP_PORT 1025)"]=mailpit
    ["$(env_value MAILPIT_UI_PORT 8025)"]=mailpit
  )
  for port in "${!port_services[@]}"; do
    service="${port_services[$port]}"
    if [[ -n "${service_containers[$service]:-}" ]]; then
      ok "A porta local $port pertence ao serviço esperado ($service)."
    elif port_is_listening "$port"; then
      failed "A porta $port já está ocupada por outro processo; ela é necessária para $service."
    else
      port_result=$?
      if [[ "$port_result" == "2" ]]; then
        warning "Não foi possível inspecionar a porta $port porque o comando ss não está disponível."
      else
        ok "A porta local $port está livre para $service."
      fi
    fi
  done

  backend_port="$(env_value BACKEND_PORT 8000)"
  frontend_port="$(env_value FRONTEND_PORT 3000)"
  mailpit_port="$(env_value MAILPIT_UI_PORT 8025)"
  if curl --fail --silent --max-time 3 "http://127.0.0.1:$backend_port/api/v1/health/live" >/dev/null 2>&1; then
    ok "A liveness do backend respondeu."
  else
    failed "A liveness do backend não respondeu em /api/v1/health/live."
  fi
  if curl --fail --silent --max-time 3 "http://127.0.0.1:$backend_port/api/v1/health/ready" >/dev/null 2>&1; then
    ok "A readiness do backend confirmou o banco."
  else
    failed "A readiness do backend falhou. Confira PostgreSQL e migrations."
  fi
  if curl --fail --silent --max-time 3 "http://127.0.0.1:$frontend_port/api/health" >/dev/null 2>&1; then
    ok "O frontend respondeu ao healthcheck."
  else
    failed "O frontend não respondeu em /api/health."
  fi
  if curl --fail --silent --max-time 3 "http://127.0.0.1:$mailpit_port/api/v1/messages" >/dev/null 2>&1; then
    ok "O Mailpit respondeu sem enviar e-mail para fora."
  else
    failed "A API local do Mailpit não respondeu."
  fi

  if [[ -n "${service_containers[backend]:-}" ]]; then
    current_revision="$(docker compose exec -T backend alembic current 2>/dev/null | awk 'NR == 1 {print $1}')"
    head_revision="$(docker compose exec -T backend alembic heads 2>/dev/null | awk 'NR == 1 {print $1}')"
    if [[ -n "$current_revision" && "$current_revision" == "$head_revision" ]]; then
      ok "O banco está na migration head ($current_revision)."
    else
      failed "O banco não está na migration head (atual: ${current_revision:-indisponível}; head: ${head_revision:-indisponível})."
    fi
    if docker compose exec -T backend python -c '
from urllib.parse import urlparse
from minio import Minio
from growthos.config import get_settings
s = get_settings()
u = urlparse(s.s3_endpoint_url)
c = Minio(u.netloc, access_key=s.s3_access_key_id, secret_key=s.s3_secret_access_key, secure=u.scheme == "https", region=s.s3_region)
raise SystemExit(0 if c.bucket_exists(s.s3_bucket) else 1)
' >/dev/null 2>&1; then
      ok "O bucket privado configurado está acessível pelo backend."
    else
      failed "O backend não conseguiu acessar o bucket configurado."
    fi
  fi
fi

job_timeout="$(env_value JOB_TIMEOUT_SECONDS 120)"
heartbeat_age="$(env_value WORKER_HEARTBEAT_MAX_AGE_SECONDS 150)"
stop_grace="$(env_value WORKER_STOP_GRACE_PERIOD_SECONDS 150)"
if positive_integer "$job_timeout" && positive_integer "$heartbeat_age" && ((heartbeat_age > job_timeout)); then
  ok "Heartbeat do worker ($heartbeat_age s) é maior que o timeout de job ($job_timeout s)."
else
  failed "WORKER_HEARTBEAT_MAX_AGE_SECONDS precisa ser maior que JOB_TIMEOUT_SECONDS."
fi
if positive_integer "$job_timeout" && positive_integer "$stop_grace" && ((stop_grace > job_timeout)); then
  ok "Grace period do worker ($stop_grace s) permite encerrar um job de $job_timeout s."
else
  failed "WORKER_STOP_GRACE_PERIOD_SECONDS precisa ser maior que JOB_TIMEOUT_SECONDS."
fi

printf '\nResumo: %d OK, %d aviso(s), %d erro(s).\n' \
  "$checks_ok" "$checks_warning" "$checks_failed"
if ((checks_failed)); then
  printf 'O ambiente ainda não está pronto. Corrija os itens marcados como ERRO e rode make doctor novamente.\n' >&2
  exit 1
fi
printf 'O ambiente está pronto para uso local.\n'
