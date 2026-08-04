#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/operations.sh
source "$ROOT_DIR/scripts/lib/operations.sh"
cd "$ROOT_DIR"

operations_require_command docker
operations_require_command realpath
operations_require_command sha256sum
docker compose version >/dev/null

BACKUP_ROOT="$(operations_backup_root "$ROOT_DIR")"
requested_backup="${1:-}"
if [[ -z "$requested_backup" ]]; then
  requested_backup="$(operations_latest_backup "$BACKUP_ROOT")"
fi
if [[ -z "$requested_backup" ]]; then
  echo "Nenhum backup foi encontrado para o teste de restauração." >&2
  exit 1
fi
BACKUP_DIR="$(operations_assert_backup_path "$BACKUP_ROOT" "$requested_backup")"
"$ROOT_DIR/scripts/backup-verify.sh" "$BACKUP_DIR"

PROJECT_NAME="devmark-growthos-restore-$(date -u +'%Y%m%d%H%M%S')-$$"
case "$PROJECT_NAME" in
  devmark-growthos-restore-*) ;;
  *) echo "Nome inseguro para projeto de restauração." >&2; exit 1 ;;
esac
COMPOSE_FILE="$ROOT_DIR/infra/compose.restore-test.yml"
WORK_DIR="$(mktemp -d "$BACKUP_ROOT/.restore-work.XXXXXX")"
chmod 700 "$WORK_DIR"
export RESTORE_BACKUP_DIR="$BACKUP_DIR"
export RESTORE_WORK_DIR="$WORK_DIR"

cleanup_restore() {
  local exit_code=$?
  trap - EXIT
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile tools \
    down -v --remove-orphans >/dev/null 2>&1 || exit_code=1
  rm -rf -- "$WORK_DIR"
  exit "$exit_code"
}
handle_signal() {
  exit 130
}
trap cleanup_restore EXIT
trap handle_signal INT TERM

operations_log "Criando ambiente isolado $PROJECT_NAME, sem portas publicadas."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --wait postgres minio
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" run --rm -T minio-init

operations_log "Restaurando o dump PostgreSQL no banco descartável."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile tools run --rm -T \
  db-tool sh -ec \
  'pg_restore --exit-on-error --no-owner --no-acl --host=postgres --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" /backup/postgres.dump'

operations_log "Restaurando os objetos no MinIO descartável."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile tools run --rm -T \
  --user "$(id -u):$(id -g)" \
  --entrypoint /bin/sh minio-tool -ec \
  'mc alias set restored http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mirror --overwrite /backup/minio "restored/$S3_BUCKET" && mc mirror --overwrite "restored/$S3_BUCKET" /work/minio'

operations_log "Conferindo checksums dos objetos restaurados."
grep '  minio/' "$BACKUP_DIR/SHA256SUMS" > "$WORK_DIR/minio-SHA256SUMS" || true
if [[ -s "$WORK_DIR/minio-SHA256SUMS" ]]; then
  (cd "$WORK_DIR" && sha256sum --check --strict minio-SHA256SUMS)
fi

while IFS= read -r object_key; do
  if ! operations_validate_media_key "$object_key"; then
    echo "A restauração produziu uma chave de mídia insegura." >&2
    exit 1
  fi
  if [[ ! -f "$WORK_DIR/minio/$object_key" ]]; then
    echo "A restauração não recuperou a mídia referenciada: $object_key" >&2
    exit 1
  fi
done < "$BACKUP_DIR/media-object-keys.txt"

query_scalar() {
  local query="${1:?consulta obrigatória}"
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile tools run --rm -T \
    db-tool psql --no-align --tuples-only --host=postgres --username=growthos_restore_test \
    --dbname=growthos_restore_test --command="$query" | tr -d '[:space:]'
}

for count_key in organization business media; do
  case "$count_key" in
    organization) table_name=organizations ;;
    business) table_name=businesses ;;
    media) table_name=media_assets ;;
  esac
  expected="$(sed -n "s/^${count_key}_count=//p" "$BACKUP_DIR/manifest.txt")"
  actual="$(query_scalar "SELECT count(*) FROM $table_name")"
  if [[ "$actual" != "$expected" ]]; then
    echo "Contagem divergente após restore: $table_name ($actual, esperado $expected)." >&2
    exit 1
  fi
done

expected_revision="$(sed -n 's/^alembic_revision=//p' "$BACKUP_DIR/manifest.txt")"
actual_revision="$(query_scalar 'SELECT version_num FROM alembic_version')"
if [[ "$actual_revision" != "$expected_revision" ]]; then
  echo "Revisão Alembic divergente após restore ($actual_revision, esperado $expected_revision)." >&2
  exit 1
fi

operations_log "Validando o schema restaurado com a imagem do backend."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile tools run --rm -T \
  backend-check alembic current | grep -F "$expected_revision" >/dev/null

operations_log "Teste de restauração concluído com sucesso; o ambiente será descartado."
