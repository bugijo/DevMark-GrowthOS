import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from growthos.config import Settings
from growthos.models import Membership, User

_password_hash = PasswordHash.recommended()
_dummy_hash = _password_hash.hash("growthos-invalid-password")


class InvalidSession(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    candidate = password_hash or _dummy_hash
    try:
        verified = _password_hash.verify(password, candidate)
    except (TypeError, ValueError):
        return False
    return verified and password_hash is not None


def create_session_token(
    user: User,
    membership: Membership,
    settings: Settings,
) -> tuple[str, str]:
    now = datetime.now(UTC)
    csrf_token = secrets.token_urlsafe(32)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "mid": str(membership.id),
        "org": str(membership.organization_id),
        "role": membership.role.value,
        "business": str(membership.business_id) if membership.business_id else None,
        "sv": user.session_version,
        "csrf": csrf_token,
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    token = jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")
    return token, csrf_token


def decode_session_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
        UUID(str(payload["sub"]))
        UUID(str(payload["mid"]))
        UUID(str(payload["org"]))
        if not isinstance(payload.get("csrf"), str):
            raise InvalidSession("Sessão sem proteção CSRF")
        if not isinstance(payload.get("sv"), int):
            raise InvalidSession("Sessão sem versão válida")
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidSession("Sessão inválida ou expirada") from exc
    return payload
