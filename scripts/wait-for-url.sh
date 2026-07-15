#!/usr/bin/env bash
set -euo pipefail

URL="${1:?Uso: wait-for-url.sh URL [TENTATIVAS]}"
ATTEMPTS="${2:-60}"

for ((attempt = 1; attempt <= ATTEMPTS; attempt += 1)); do
  if curl --fail --silent --show-error --max-time 3 "$URL" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 2
done

echo "Tempo esgotado aguardando $URL" >&2
exit 1

