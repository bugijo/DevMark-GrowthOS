#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/lib/operations.sh
source "$ROOT_DIR/scripts/lib/operations.sh"

work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT

mkdir -p \
  "$work_dir/20260715T120000Z-older" \
  "$work_dir/20260716T223524Z-newer" \
  "$work_dir/.20260717T010000Z-partial"

latest="$(operations_latest_backup "$work_dir")"
[[ "$(basename "$latest")" == "20260716T223524Z-newer" ]]

operations_validate_media_key \
  "organizations/organization-id/businesses/business-id/media/image.png"
! operations_validate_media_key "../outside.png"
! operations_validate_media_key "/absolute.png"

inside="$(operations_assert_backup_path "$work_dir" "$latest")"
[[ "$inside" == "$latest" ]]
! operations_assert_backup_path "$work_dir" "$ROOT_DIR" >/dev/null 2>&1

printf 'Testes dos utilitários operacionais: OK\n'
