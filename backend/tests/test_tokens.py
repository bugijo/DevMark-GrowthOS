import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from growthos.services.tokens import (
    TokenPurpose,
    derive_token,
    expiration_for,
    hash_token,
    hashes_match,
    issue_token,
    require_utc,
    token_id_from_value,
    verify_token,
)

SECRET = "test-only-token-secret-with-at-least-thirty-two-bytes"
TOKEN_ID = UUID("12345678-1234-5678-9234-567812345678")
NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def test_derivation_uses_hmac_sha256_and_domain_separation() -> None:
    message = b"devmark-growthos:one-time-token:v1\x00organization_invite\x00" + TOKEN_ID.bytes
    signature = (
        base64.urlsafe_b64encode(hmac.new(SECRET.encode(), message, hashlib.sha256).digest())
        .rstrip(b"=")
        .decode()
    )
    expected = f"{TOKEN_ID.hex}.{signature}"

    assert derive_token(SECRET, TokenPurpose.ORGANIZATION_INVITE, TOKEN_ID) == expected
    assert derive_token(SECRET, TokenPurpose.PASSWORD_RESET, TOKEN_ID) != expected
    assert (
        derive_token(
            SECRET,
            TokenPurpose.ORGANIZATION_INVITE,
            UUID("12345678-1234-5678-9234-567812345679"),
        )
        != expected
    )
    assert token_id_from_value(expected) == TOKEN_ID
    assert token_id_from_value("invalid") is None


def test_issue_token_is_deterministic_for_identifier_and_dates() -> None:
    issued = issue_token(
        SECRET,
        TokenPurpose.PASSWORD_RESET,
        timedelta(minutes=30),
        token_id=TOKEN_ID,
        now=NOW,
    )
    repeated = issue_token(
        SECRET,
        TokenPurpose.PASSWORD_RESET,
        timedelta(minutes=30),
        token_id=TOKEN_ID,
        now=NOW,
    )

    assert issued == repeated
    assert issued.token_hash == hash_token(issued.value)
    assert issued.issued_at == NOW
    assert issued.expires_at == NOW + timedelta(minutes=30)


def test_hash_matching_accepts_only_the_original_value() -> None:
    token = derive_token(SECRET, TokenPurpose.ORGANIZATION_INVITE, TOKEN_ID)
    expected_hash = hash_token(token)

    assert hashes_match(token, expected_hash)
    assert not hashes_match(f"{token}x", expected_hash)
    assert not hashes_match(token, "not-a-valid-hash")
    assert not hashes_match("x" * 10_000, expected_hash)


def test_verify_token_checks_secret_purpose_identifier_hash_and_expiration() -> None:
    issued = issue_token(
        SECRET,
        TokenPurpose.ORGANIZATION_INVITE,
        timedelta(hours=24),
        token_id=TOKEN_ID,
        now=NOW,
    )
    common = {
        "secret": SECRET,
        "purpose": issued.purpose,
        "token_id": issued.token_id,
        "expected_hash": issued.token_hash,
        "expires_at": issued.expires_at,
        "now": NOW,
    }

    assert verify_token(issued.value, **common)
    assert not verify_token(f"{issued.value}x", **common)
    assert not verify_token(issued.value, **{**common, "expected_hash": "0" * 64})
    assert not verify_token(
        issued.value,
        **{**common, "purpose": TokenPurpose.PASSWORD_RESET},
    )
    assert not verify_token(
        issued.value,
        **{**common, "token_id": UUID("12345678-1234-5678-9234-567812345679")},
    )


def test_token_is_invalid_at_expiration_and_after_use_or_revocation() -> None:
    issued = issue_token(
        SECRET,
        TokenPurpose.PASSWORD_RESET,
        timedelta(minutes=30),
        token_id=TOKEN_ID,
        now=NOW,
    )
    common = {
        "secret": SECRET,
        "purpose": issued.purpose,
        "token_id": issued.token_id,
        "expected_hash": issued.token_hash,
        "expires_at": issued.expires_at,
    }

    assert verify_token(issued.value, **common, now=issued.expires_at - timedelta(microseconds=1))
    assert not verify_token(issued.value, **common, now=issued.expires_at)
    assert not verify_token(issued.value, **common, used_at=NOW, now=NOW)
    assert not verify_token(issued.value, **common, revoked_at=NOW, now=NOW)


def test_dates_must_be_timezone_aware_and_ttl_positive() -> None:
    naive = datetime(2026, 7, 15, 12, 0)

    with pytest.raises(ValueError, match="fuso horário"):
        require_utc(naive, field_name="value")
    with pytest.raises(ValueError, match="ttl deve ser positivo"):
        expiration_for(timedelta(0), now=NOW)
    with pytest.raises(ValueError, match="ao menos 32 bytes"):
        derive_token("short", TokenPurpose.PASSWORD_RESET, TOKEN_ID)
