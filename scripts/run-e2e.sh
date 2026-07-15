#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

docker compose up --build -d postgres minio minio-init backend worker frontend
./scripts/wait-for-url.sh http://localhost:8000/api/v1/health 90
./scripts/wait-for-url.sh http://localhost:3000/api/health 90
docker compose --profile test run --rm --build e2e

