#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/operations.sh
source "$ROOT_DIR/scripts/lib/operations.sh"
cd "$ROOT_DIR"

operations_require_command docker
operations_require_command git
operations_require_command realpath
operations_require_command sha256sum
docker compose version >/dev/null

BACKUP_ROOT="$(operations_backup_root "$ROOT_DIR")"
BACKUP_ROOT="$(operations_canonical_path "$BACKUP_ROOT")"
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-7}"
QUIESCE="${BACKUP_QUIESCE:-true}"

if [[ ! "$RETENTION_COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "BACKUP_RETENTION_COUNT precisa ser um inteiro positivo." >&2
  exit 1
fi
if [[ "$QUIESCE" != "true" ]]; then
  echo "BACKUP_QUIESCE=false foi recusado: banco e objetos poderiam ficar inconsistentes." >&2
  exit 1
fi

mkdir -p -- "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
LOCK_DIR="$BACKUP_ROOT/.backup.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Já existe uma operação de backup em andamento em $BACKUP_ROOT." >&2
  exit 1
fi

BACKUP_ID="$(date -u +'%Y%m%dT%H%M%SZ')-$(git rev-parse --short=12 HEAD)"
PARTIAL_DIR="$BACKUP_ROOT/.${BACKUP_ID}.partial"
FINAL_DIR="$BACKUP_ROOT/$BACKUP_ID"
BACKEND_WAS_RUNNING=false
WORKER_WAS_RUNNING=false
BACKUP_PUBLISHED=false

restore_runtime() {
  local exit_code=$?
  trap - EXIT
  if [[ "$BACKEND_WAS_RUNNING" == "true" ]]; then
    docker compose up -d --no-deps backend >/dev/null 2>&1 || exit_code=1
    "$ROOT_DIR/scripts/wait-for-service-health.sh" backend 90 >/dev/null 2>&1 \
      || exit_code=1
  fi
  if [[ "$WORKER_WAS_RUNNING" == "true" ]]; then
    docker compose up -d --no-deps worker >/dev/null 2>&1 || exit_code=1
    "$ROOT_DIR/scripts/wait-for-service-health.sh" worker 90 >/dev/null 2>&1 \
      || exit_code=1
  fi
  if [[ "$BACKUP_PUBLISHED" != "true" ]]; then
    rm -rf -- "$PARTIAL_DIR"
  fi
  rmdir "$LOCK_DIR" 2>/dev/null || true
  exit "$exit_code"
}
handle_signal() {
  exit 130
}
trap restore_runtime EXIT
trap handle_signal INT TERM

mkdir -p "$PARTIAL_DIR/minio"
chmod 700 "$PARTIAL_DIR"
exec > >(tee -a "$PARTIAL_DIR/backup.log") 2>&1

operations_log "Validando a stack fonte."
docker compose config --quiet
for service in postgres minio; do
  container_id="$(docker compose ps -q "$service")"
  if [[ -z "$container_id" ]]; then
    echo "O serviço $service não está em execução. Rode make setup." >&2
    exit 1
  fi
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")"
  if [[ "$health" != "healthy" ]]; then
    echo "O serviço $service não está saudável (estado: $health)." >&2
    exit 1
  fi
done

if [[ -n "$(docker compose ps -q backend)" ]]; then
  BACKEND_WAS_RUNNING=true
fi
if [[ -n "$(docker compose ps -q worker)" ]]; then
  WORKER_WAS_RUNNING=true
fi

operations_log "Suspendendo temporariamente os processos que escrevem dados."
services_to_stop=()
[[ "$WORKER_WAS_RUNNING" == "true" ]] && services_to_stop+=(worker)
[[ "$BACKEND_WAS_RUNNING" == "true" ]] && services_to_stop+=(backend)
if ((${#services_to_stop[@]})); then
  docker compose stop "${services_to_stop[@]}"
fi

operations_log "Exportando PostgreSQL em formato restaurável."
docker compose exec -T postgres sh -ec \
  'exec pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  > "$PARTIAL_DIR/postgres.dump"

docker compose exec -T postgres sh -ec \
  'exec psql --no-align --tuples-only --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT object_key FROM media_assets ORDER BY object_key"' \
  > "$PARTIAL_DIR/media-object-keys.txt"

ALEMBIC_REVISION="$(
  docker compose exec -T postgres sh -ec \
    'exec psql --no-align --tuples-only --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT version_num FROM alembic_version"' \
    | tr -d '[:space:]'
)"
ORGANIZATION_COUNT="$(docker compose exec -T postgres sh -ec \
  'exec psql --no-align --tuples-only --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT count(*) FROM organizations"' | tr -d '[:space:]')"
BUSINESS_COUNT="$(docker compose exec -T postgres sh -ec \
  'exec psql --no-align --tuples-only --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT count(*) FROM businesses"' | tr -d '[:space:]')"
MEDIA_COUNT="$(docker compose exec -T postgres sh -ec \
  'exec psql --no-align --tuples-only --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT count(*) FROM media_assets"' | tr -d '[:space:]')"

operations_log "Copiando os objetos privados do MinIO."
docker compose run --rm --no-deps -T \
  --user "$(id -u):$(id -g)" \
  -e MC_CONFIG_DIR=/tmp/.mc \
  -v "$PARTIAL_DIR/minio:/backup" \
  --entrypoint /bin/sh minio-init -ec \
  'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mirror --overwrite "local/$S3_BUCKET" /backup'

while IFS= read -r object_key; do
  if ! operations_validate_media_key "$object_key"; then
    echo "O banco contém uma chave de mídia insegura; backup interrompido." >&2
    exit 1
  fi
  if [[ ! -f "$PARTIAL_DIR/minio/$object_key" ]]; then
    echo "Objeto referenciado pelo banco não foi encontrado no backup: $object_key" >&2
    exit 1
  fi
done < "$PARTIAL_DIR/media-object-keys.txt"

OBJECT_COUNT="$(find "$PARTIAL_DIR/minio" -type f -print | wc -l | tr -d '[:space:]')"
cat > "$PARTIAL_DIR/manifest.txt" <<EOF
format_version=1
created_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
git_commit=$(git rev-parse HEAD)
alembic_revision=$ALEMBIC_REVISION
organization_count=$ORGANIZATION_COUNT
business_count=$BUSINESS_COUNT
media_count=$MEDIA_COUNT
object_count=$OBJECT_COUNT
EOF

operations_log "Calculando checksums."
(
  cd "$PARTIAL_DIR"
  find postgres.dump media-object-keys.txt manifest.txt minio -type f -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)

BACKUP_VERIFY_ALLOW_PARTIAL=1 "$ROOT_DIR/scripts/backup-verify.sh" "$PARTIAL_DIR"
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$PARTIAL_DIR/VERIFIED"
chmod -R go-rwx "$PARTIAL_DIR"
mv -- "$PARTIAL_DIR" "$FINAL_DIR"
BACKUP_PUBLISHED=true
operations_log "Backup publicado com segurança em $FINAL_DIR."

mapfile -t old_backups < <(
  find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z-*' -print \
    | LC_ALL=C sort -r \
    | tail -n "+$((RETENTION_COUNT + 1))"
)
for old_backup in "${old_backups[@]}"; do
  if [[ -f "$old_backup/VERIFIED" ]]; then
    operations_log "Removendo backup local antigo já verificado: $(basename "$old_backup")"
    rm -rf -- "$old_backup"
  fi
done
