#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
report_dir="$ROOT_DIR/.data/cav1-23"
report_file="$report_dir/cav1-23-$timestamp.log"
failures=0
passes=0

mkdir -p "$report_dir"
exec > >(tee -a "$report_file") 2>&1

pass() {
  passes=$((passes + 1))
  printf 'PASS  %s\n' "$1"
}

fail() {
  failures=$((failures + 1))
  printf 'FAIL  %s\n' "$1"
}

run_check() {
  local label="${1:?descrição obrigatória}"
  shift
  printf '\n### %s\n' "$label"
  "$@"
  local status=$?
  if ((status == 0)); then
    pass "$label"
  else
    fail "$label (código $status)"
  fi
}

command_check() {
  local command_name="${1:?comando obrigatório}"
  if command -v "$command_name" >/dev/null 2>&1; then
    pass "Comando disponível: $command_name"
  else
    fail "Comando ausente: $command_name"
  fi
}

port_available_or_owned() {
  local port="${1:?porta obrigatória}"
  local service="${2:?serviço obrigatório}"
  local container_port="${3:?porta do container obrigatória}"
  local published
  published="$(docker compose port "$service" "$container_port" 2>/dev/null || true)"
  if [[ "$published" == *":$port" ]]; then
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    ! ss -H -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${port}$"
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi
  return 1
}

memory_megabytes() {
  if [[ -r /proc/meminfo ]]; then
    awk '/MemTotal:/ {printf "%d", $2 / 1024}' /proc/meminfo
  elif command -v sysctl >/dev/null 2>&1; then
    sysctl -n hw.memsize 2>/dev/null | awk '{printf "%d", $1 / 1024 / 1024}'
  fi
}

verify_memory() {
  local memory_mb
  memory_mb="$(memory_megabytes)"
  printf 'Memória detectada: %s MiB\n' "${memory_mb:-indisponível}"
  [[ "$memory_mb" =~ ^[0-9]+$ ]] && ((memory_mb >= 4096))
}

verify_disk() {
  local available_mb
  available_mb="$(df -Pm "$ROOT_DIR" | awk 'NR == 2 {print $4}')"
  printf 'Disco livre detectado: %s MiB\n' "${available_mb:-indisponível}"
  [[ "$available_mb" =~ ^[0-9]+$ ]] && ((available_mb >= 10240))
}

verify_docker() {
  local version major
  docker info >/dev/null
  version="$(docker version --format '{{.Server.Version}}')"
  major="${version%%.*}"
  printf 'Docker Server detectado: %s\n' "$version"
  [[ "$major" =~ ^[0-9]+$ ]] && ((major >= 24))
}

verify_compose() {
  local version major
  version="$(docker compose version --short)"
  major="${version%%.*}"
  printf 'Docker Compose detectado: %s\n' "$version"
  [[ "$major" == "2" ]]
}

verify_clean_clone() {
  local branch
  git rev-parse --is-inside-work-tree
  git status --short --branch
  git rev-parse HEAD
  branch="$(git branch --show-current)"
  [[ "$branch" == "agent/fechamento-v1" ]]
  [[ -z "$(git status --porcelain --untracked-files=all)" ]]
}

verify_env() {
  [[ -f .env ]]
  git check-ignore -q .env
  cmp -s .env .env.example
}

verify_migrations() {
  docker compose exec -T backend sh -c '
current="$(alembic current 2>/dev/null | awk "NR == 1 {print \$1}")"
head="$(alembic heads 2>/dev/null | awk "NR == 1 {print \$1}")"
printf "Migration atual: %s; head: %s\n" "$current" "$head"
test -n "$current" && test "$current" = "$head"
'
}

verify_seed() {
  docker compose exec -T postgres sh -c '
result="$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "
SELECT
  EXISTS (SELECT 1 FROM organizations WHERE name = '\''DevMark Demo'\'')
  AND EXISTS (SELECT 1 FROM users WHERE email = '\''admin@devmark.local'\'')
  AND EXISTS (SELECT 1 FROM users WHERE email = '\''client@clinicafeliz.local'\'');
")"
printf "Seed fictício presente: %s\n" "$result"
test "$result" = "t"
'
}

printf 'Validação independente CAV1-23 — verificador opcional\n'
printf 'Início UTC: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'Diretório: %s\n' "$ROOT_DIR"
printf 'Log: %s\n' "$report_file"
printf 'Este script registra falhas e não altera código nem corrige configuração.\n\n'

for required_command in git make docker curl awk tee cmp; do
  command_check "$required_command"
done

run_check "Docker Engine 24 ou superior" verify_docker
run_check "Docker Compose v2" verify_compose
run_check "Memória mínima de 4 GiB" verify_memory
run_check "Disco livre mínimo de 10 GiB" verify_disk
run_check "Clone Git limpo" verify_clean_clone
run_check ".env existe, está ignorado e permanece igual ao exemplo" verify_env

declare -a port_checks=(
  "1025 mailpit 1025"
  "3000 frontend 3000"
  "5432 postgres 5432"
  "8000 backend 8000"
  "8025 mailpit 8025"
  "9000 minio 9000"
  "9001 minio 9001"
)
for port_check in "${port_checks[@]}"; do
  read -r port service container_port <<<"$port_check"
  run_check "Porta $port livre ou pertencente ao serviço $service" \
    port_available_or_owned "$port" "$service" "$container_port"
done

run_check "make setup" make setup
run_check "make doctor" make doctor
run_check "make status" make status
run_check "Frontend acessível" curl --fail --silent --show-error --output /dev/null --max-time 10 \
  http://127.0.0.1:3000/api/health
run_check "Backend acessível" curl --fail --silent --show-error --output /dev/null --max-time 10 \
  http://127.0.0.1:8000/api/v1/health/ready
run_check "Mailpit acessível" curl --fail --silent --show-error --output /dev/null --max-time 10 \
  http://127.0.0.1:8025/api/v1/messages
run_check "Migrações aplicadas até o head" verify_migrations
run_check "Seed fictício presente" verify_seed
run_check "Testes essenciais E2E" make e2e

printf '\nFim UTC: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'Resumo: %d PASS, %d FAIL\n' "$passes" "$failures"
printf 'Relatório: %s\n' "$report_file"

if ((failures > 0)); then
  printf 'Resultado do verificador: FAIL\n'
  exit 1
fi

printf 'Resultado do verificador: PASS\n'
