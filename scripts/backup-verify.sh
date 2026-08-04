#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/operations.sh
source "$ROOT_DIR/scripts/lib/operations.sh"
cd "$ROOT_DIR"

operations_require_command docker
operations_require_command realpath
operations_require_command sha256sum

BACKUP_ROOT="$(operations_backup_root "$ROOT_DIR")"
mkdir -p "$BACKUP_ROOT"
requested_backup="${1:-}"
if [[ -z "$requested_backup" ]]; then
  requested_backup="$(operations_latest_backup "$BACKUP_ROOT")"
fi
if [[ -z "$requested_backup" ]]; then
  echo "Nenhum backup foi encontrado em $BACKUP_ROOT." >&2
  exit 1
fi
BACKUP_DIR="$(operations_assert_backup_path "$BACKUP_ROOT" "$requested_backup")"

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "Diretório de backup não encontrado: $BACKUP_DIR" >&2
  exit 1
fi
if [[ "${BACKUP_VERIFY_ALLOW_PARTIAL:-0}" != "1" && "$(basename "$BACKUP_DIR")" == .* ]]; then
  echo "Backup parcial não pode ser validado como cópia final." >&2
  exit 1
fi
if find "$BACKUP_DIR" -type l -print -quit | grep -q .; then
  echo "Backup rejeitado porque contém link simbólico." >&2
  exit 1
fi

for required_file in postgres.dump media-object-keys.txt manifest.txt SHA256SUMS; do
  if [[ ! -f "$BACKUP_DIR/$required_file" ]]; then
    echo "Backup incompleto: falta $required_file." >&2
    exit 1
  fi
done

operations_log "Verificando checksums de $(basename "$BACKUP_DIR")."
(
  cd "$BACKUP_DIR"
  sha256sum --check --strict SHA256SUMS
)

if ! grep -qx 'format_version=1' "$BACKUP_DIR/manifest.txt"; then
  echo "Versão de manifesto ausente ou incompatível." >&2
  exit 1
fi
for numeric_key in organization_count business_count media_count object_count; do
  value="$(sed -n "s/^${numeric_key}=//p" "$BACKUP_DIR/manifest.txt")"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "Manifesto inválido: $numeric_key não é numérico." >&2
    exit 1
  fi
done
revision="$(sed -n 's/^alembic_revision=//p' "$BACKUP_DIR/manifest.txt")"
if [[ ! "$revision" =~ ^[0-9A-Za-z_-]+$ ]]; then
  echo "Manifesto inválido: revisão Alembic ausente." >&2
  exit 1
fi

while IFS= read -r object_key; do
  if ! operations_validate_media_key "$object_key"; then
    echo "Backup rejeitado porque contém chave de mídia insegura." >&2
    exit 1
  fi
  if [[ ! -f "$BACKUP_DIR/minio/$object_key" ]]; then
    echo "Backup incompleto: mídia referenciada não encontrada ($object_key)." >&2
    exit 1
  fi
done < "$BACKUP_DIR/media-object-keys.txt"

operations_log "Validando o catálogo interno do dump PostgreSQL."
docker run --rm -i postgres:16-alpine pg_restore --list \
  < "$BACKUP_DIR/postgres.dump" >/dev/null

operations_log "Backup íntegro: $BACKUP_DIR"
