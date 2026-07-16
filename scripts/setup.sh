#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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
./scripts/wait-for-url.sh http://localhost:8000/api/v1/health 90
./scripts/wait-for-url.sh http://localhost:3000/api/health 90
./scripts/wait-for-service-health.sh worker 90

echo "GrowthOS disponível em http://localhost:3000"
echo "OpenAPI disponível em http://localhost:8000/docs"
