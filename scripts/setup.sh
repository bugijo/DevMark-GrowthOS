#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/operations.sh
source "$ROOT_DIR/scripts/lib/operations.sh"
cd "$ROOT_DIR"

command -v docker >/dev/null || { echo "Docker não encontrado." >&2; exit 1; }
command -v curl >/dev/null || { echo "curl não encontrado." >&2; exit 1; }
docker compose version >/dev/null

if [[ ! -f .env ]]; then
  (umask 077 && cp .env.example .env)
  echo "Arquivo .env local criado a partir de .env.example."
fi
chmod 600 .env 2>/dev/null || true

docker compose config --quiet
docker compose up --build -d
backend_port="$(operations_env_value .env BACKEND_PORT 8000)"
frontend_port="$(operations_env_value .env FRONTEND_PORT 3000)"
./scripts/wait-for-url.sh "http://localhost:$backend_port/api/v1/health/ready" 90
./scripts/wait-for-url.sh "http://localhost:$frontend_port/api/health" 90
./scripts/wait-for-service-health.sh worker 90

echo "GrowthOS disponível em http://localhost:$frontend_port"
echo "OpenAPI disponível em http://localhost:$backend_port/docs"
