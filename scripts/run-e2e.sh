#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v docker >/dev/null || { echo "Docker não encontrado." >&2; exit 1; }
command -v curl >/dev/null || { echo "curl não encontrado." >&2; exit 1; }
docker compose version >/dev/null

if [[ ! -f .env ]]; then
  (umask 077 && cp .env.example .env)
fi
chmod 600 .env 2>/dev/null || true

runtime_overridden=0

restore_local_runtime() {
  local original_exit_code=$?
  local restore_exit_code=0
  trap - EXIT

  # Em falha, preserve os contêineres e logs exatamente no estado do teste.
  # A configuração voltada ao navegador é restaurada somente após sucesso.
  if (( runtime_overridden && original_exit_code == 0 )); then
    echo "Restaurando endpoint público local do MinIO no backend e no worker..."
    docker compose up -d --no-deps --force-recreate backend worker \
      || restore_exit_code=$?
    if (( restore_exit_code == 0 )); then
      ./scripts/wait-for-url.sh http://localhost:8000/api/v1/health 90 \
        || restore_exit_code=$?
      ./scripts/wait-for-service-health.sh worker 90 \
        || restore_exit_code=$?
    fi
  fi

  if (( original_exit_code == 0 && restore_exit_code != 0 )); then
    original_exit_code=$restore_exit_code
  fi
  exit "$original_exit_code"
}

trap restore_local_runtime EXIT
runtime_overridden=1

S3_PUBLIC_ENDPOINT_URL=http://minio:9000 \
  docker compose up --build -d postgres minio minio-init backend worker frontend
./scripts/wait-for-url.sh http://localhost:8000/api/v1/health 90
./scripts/wait-for-url.sh http://localhost:3000/api/health 90
./scripts/wait-for-service-health.sh worker 90
S3_PUBLIC_ENDPOINT_URL=http://minio:9000 \
  docker compose --profile test run --rm --build e2e
