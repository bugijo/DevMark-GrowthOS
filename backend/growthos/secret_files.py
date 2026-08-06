from __future__ import annotations

import os
import stat
from pathlib import Path

from growthos.config_errors import UnsafeConfigurationError


def read_private_secret_file(raw_path: str, *, variable_name: str) -> str:
    path = Path(raw_path).expanduser()
    try:
        file_stat = path.stat()
    except OSError as exc:
        raise UnsafeConfigurationError(
            f"{variable_name} não aponta para um arquivo de segredo acessível"
        ) from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise UnsafeConfigurationError(f"{variable_name} deve apontar para um arquivo regular")
    if file_stat.st_uid not in {0, os.geteuid()}:
        raise UnsafeConfigurationError(
            f"{variable_name} deve pertencer ao usuário do processo ou ao root"
        )
    if file_stat.st_mode & 0o077:
        raise UnsafeConfigurationError(
            f"{variable_name} deve bloquear acesso de grupo e outros (modo 600 ou 400)"
        )
    if file_stat.st_size > 16_384:
        raise UnsafeConfigurationError(f"{variable_name} excede o tamanho máximo permitido")
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise UnsafeConfigurationError(f"{variable_name} não pôde ser lido") from exc
    if not value:
        raise UnsafeConfigurationError(f"{variable_name} está vazio")
    if "\n" in value or "\r" in value:
        raise UnsafeConfigurationError(f"{variable_name} deve conter somente um segredo")
    return value
