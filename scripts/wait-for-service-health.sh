#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:?Uso: wait-for-service-health.sh SERVIÇO [TENTATIVAS]}"
ATTEMPTS="${2:-60}"

for ((attempt = 1; attempt <= ATTEMPTS; attempt += 1)); do
  container_id="$(docker compose ps -q "$SERVICE")"
  if [[ -n "$container_id" ]]; then
    health="$(
      docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
        "$container_id"
    )"
    if [[ "$health" == "healthy" ]]; then
      exit 0
    fi
  fi
  sleep 2
done

echo "Tempo esgotado aguardando healthcheck de $SERVICE" >&2
docker compose ps "$SERVICE" >&2 || true
docker compose logs --no-color --tail=100 "$SERVICE" >&2 || true
exit 1
