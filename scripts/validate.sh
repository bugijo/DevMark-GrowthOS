#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose config --quiet
python3 -m compileall -q worker/src worker/tests
python3 -m json.tool shared/contracts/worker-job-v1.schema.json >/dev/null

while IFS= read -r script; do
  bash -n "$script"
done < <(find scripts -maxdepth 1 -type f -name '*.sh' -print | sort)

if command -v actionlint >/dev/null; then
  actionlint
fi

git diff --check

