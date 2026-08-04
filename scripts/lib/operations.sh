#!/usr/bin/env bash

# Biblioteca carregada apenas por scripts Bash. Não habilita opções globais para
# que cada chamador declare seu próprio contrato de erro.

operations_root_dir() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

operations_backup_root() {
  local root_dir="${1:?root_dir obrigatório}"
  printf '%s\n' "${BACKUP_ROOT:-$root_dir/.data/backups}"
}

operations_env_value() {
  local env_file="${1:?arquivo de ambiente obrigatório}"
  local key="${2:?variável obrigatória}"
  local fallback="${3-}"
  local value
  value="$(sed -n "s/^${key}=//p" "$env_file" 2>/dev/null | tail -n 1 | tr -d '\r')"
  printf '%s\n' "${value:-$fallback}"
}

operations_log() {
  local message="${1:?mensagem obrigatória}"
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$message"
}

operations_require_command() {
  local command_name="${1:?comando obrigatório}"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Comando obrigatório não encontrado: %s\n' "$command_name" >&2
    return 1
  fi
}

operations_canonical_path() {
  local path="${1:?caminho obrigatório}"
  realpath -m -- "$path"
}

operations_assert_backup_path() {
  local backup_root="${1:?raiz de backup obrigatória}"
  local candidate="${2:?backup obrigatório}"
  local canonical_root canonical_candidate
  canonical_root="$(operations_canonical_path "$backup_root")"
  canonical_candidate="$(operations_canonical_path "$candidate")"
  case "$canonical_candidate/" in
    "$canonical_root"/*) printf '%s\n' "$canonical_candidate" ;;
    *)
      printf 'O backup precisa estar dentro de %s.\n' "$canonical_root" >&2
      return 1
      ;;
  esac
}

operations_latest_backup() {
  local backup_root="${1:?raiz de backup obrigatória}"
  find "$backup_root" -mindepth 1 -maxdepth 1 -type d \
    -name '20??????T??????Z-*' -print 2>/dev/null | LC_ALL=C sort | tail -n 1
}

operations_validate_media_key() {
  local key="${1-}"
  [[ -n "$key" ]] || return 1
  [[ "$key" != /* ]] || return 1
  [[ "$key" != *'\'* ]] || return 1
  [[ "$key" != *$'\n'* && "$key" != *$'\r'* ]] || return 1
  case "/$key/" in
    */../*|*/./*) return 1 ;;
  esac
  [[ "$key" == organizations/* ]]
}
