"""Primitivas para tokens determinísticos, secretos e de uso único.

O valor apresentado ao usuário é derivado com HMAC e pode ser reproduzido por
um worker que conheça o identificador, o propósito e o segredo. Persistência deve
guardar apenas ``token_hash`` e os marcadores de uso/revogação.
"""

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

_DOMAIN_SEPARATOR = b"devmark-growthos:one-time-token:v1\x00"
_MINIMUM_SECRET_BYTES = 32
_MAX_CANDIDATE_LENGTH = 512


class TokenPurpose(StrEnum):
    ORGANIZATION_INVITE = "organization_invite"
    PASSWORD_RESET = "password_reset"


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token_id: UUID
    purpose: TokenPurpose
    value: str
    token_hash: str
    issued_at: datetime
    expires_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_utc(value: datetime, *, field_name: str) -> datetime:
    """Rejeita timestamps ingênuos e normaliza timestamps conscientes para UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} deve conter fuso horário")
    return value.astimezone(UTC)


def expiration_for(ttl: timedelta, *, now: datetime | None = None) -> datetime:
    if ttl <= timedelta(0):
        raise ValueError("ttl deve ser positivo")
    issued_at = require_utc(now or utc_now(), field_name="now")
    return issued_at + ttl


def derive_token(secret: str | bytes, purpose: TokenPurpose, token_id: UUID) -> str:
    """Deriva um valor URL-safe e inclui o identificador público do registro.

    O UUID permite uma busca indexada sem colocar e-mail, organização ou outro
    dado pessoal no link. A assinatura continua imprevisível sem o segredo.
    """

    key = _secret_bytes(secret)
    message = _DOMAIN_SEPARATOR + purpose.value.encode("ascii") + b"\x00" + token_id.bytes
    digest = hmac.new(key, message, hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"{token_id.hex}.{signature}"


def token_id_from_value(token: str) -> UUID | None:
    """Extrai somente o identificador público de um token estruturalmente válido."""

    if len(token) > _MAX_CANDIDATE_LENGTH:
        return None
    identifier, separator, signature = token.partition(".")
    if not separator or len(signature) != 43:
        return None
    try:
        return UUID(hex=identifier)
    except (AttributeError, ValueError):
        return None


def hash_token(token: str) -> str:
    """Produz o hash hexadecimal persistível de um token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(
    secret: str | bytes,
    purpose: TokenPurpose,
    ttl: timedelta,
    *,
    token_id: UUID | None = None,
    now: datetime | None = None,
) -> IssuedToken:
    issued_at = require_utc(now or utc_now(), field_name="now")
    expires_at = expiration_for(ttl, now=issued_at)
    identifier = token_id or uuid4()
    value = derive_token(secret, purpose, identifier)
    return IssuedToken(
        token_id=identifier,
        purpose=purpose,
        value=value,
        token_hash=hash_token(value),
        issued_at=issued_at,
        expires_at=expires_at,
    )


def hashes_match(candidate_token: str, expected_hash: str) -> bool:
    """Compara hash de tamanho fixo e limita entradas abusivamente grandes."""

    bounded_candidate = candidate_token if len(candidate_token) <= _MAX_CANDIDATE_LENGTH else ""
    candidate_hash = hash_token(bounded_candidate)
    normalized_expected = expected_hash.casefold()
    if len(normalized_expected) != hashlib.sha256().digest_size * 2:
        normalized_expected = "0" * (hashlib.sha256().digest_size * 2)
    return hmac.compare_digest(candidate_hash, normalized_expected)


def verify_token(
    candidate_token: str,
    *,
    secret: str | bytes,
    purpose: TokenPurpose,
    token_id: UUID,
    expected_hash: str,
    expires_at: datetime,
    used_at: datetime | None = None,
    revoked_at: datetime | None = None,
    now: datetime | None = None,
) -> bool:
    """Valida derivação, hash persistido, validade e uso único.

    As comparações secretas sempre são executadas antes da verificação de
    estado, evitando atalhos dependentes do valor do token.
    """

    current = require_utc(now or utc_now(), field_name="now")
    expiration = require_utc(expires_at, field_name="expires_at")
    if used_at is not None:
        require_utc(used_at, field_name="used_at")
    if revoked_at is not None:
        require_utc(revoked_at, field_name="revoked_at")

    expected_token = derive_token(secret, purpose, token_id)
    bounded_candidate = candidate_token if len(candidate_token) <= _MAX_CANDIDATE_LENGTH else ""
    value_matches = hmac.compare_digest(bounded_candidate, expected_token)
    stored_hash_matches = hmac.compare_digest(hash_token(expected_token), expected_hash.casefold())
    candidate_hash_matches = hashes_match(bounded_candidate, expected_hash)
    state_is_usable = used_at is None and revoked_at is None and current < expiration
    return value_matches and stored_hash_matches and candidate_hash_matches and state_is_usable


def _secret_bytes(secret: str | bytes) -> bytes:
    value = secret.encode("utf-8") if isinstance(secret, str) else secret
    if len(value) < _MINIMUM_SECRET_BYTES:
        raise ValueError("segredo de token deve ter ao menos 32 bytes")
    return value
