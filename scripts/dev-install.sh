#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  rm -rf .venv
  if ! "$PYTHON_BIN" -m venv .venv; then
    rm -rf .venv
    echo "Não foi possível criar .venv. Instale o pacote python3.12-venv e tente novamente." >&2
    exit 1
  fi
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e './backend[dev]' -e './worker[dev]'
npm --prefix frontend ci
npm --prefix tests/e2e ci
