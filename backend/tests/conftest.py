import os
from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["AUTH_SECRET_KEY"] = "tests-only-secret-key-that-is-longer-than-32-characters"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "2"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["LOGIN_RATE_LIMIT_ORIGIN_MULTIPLIER"] = "2"
os.environ["AI_PROVIDER"] = "mock"
os.environ["DEMO_CLIENT_EMAIL"] = "client@clinicafeliz.local"
os.environ["DEMO_CLIENT_PASSWORD"] = "client-password-123"

from growthos.config import get_settings
from growthos.database import configure_database, get_session_factory
from growthos.domain.enums import Role
from growthos.main import app
from growthos.models import Base, Business, Membership, Organization, User
from growthos.rate_limit import reset_login_rate_limiter
from growthos.security import hash_password

get_settings.cache_clear()


@dataclass(frozen=True)
class Identity:
    organization_id: UUID
    user_id: UUID
    membership_id: UUID
    business_id: UUID | None
    email: str
    password: str


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    engine = configure_database("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    reset_login_rate_limiter()
    yield
    reset_login_rate_limiter()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def create_identity(
    *,
    slug: str,
    email: str,
    role: Role,
    business_name: str | None = None,
    password: str = "test-password-123",
) -> Identity:
    with get_session_factory()() as session:
        organization = Organization(name=f"Organization {slug}", slug=slug)
        session.add(organization)
        session.flush()
        business: Business | None = None
        if business_name:
            business = Business(
                organization_id=organization.id,
                name=business_name,
                segment="Veterinária",
            )
            session.add(business)
            session.flush()
        user = User(
            email=email,
            name=f"User {slug}",
            password_hash=hash_password(password),
        )
        session.add(user)
        session.flush()
        membership = Membership(
            organization_id=organization.id,
            user_id=user.id,
            role=role,
            business_id=business.id if business else None,
        )
        session.add(membership)
        session.commit()
        return Identity(
            organization.id,
            user.id,
            membership.id,
            business.id if business else None,
            email,
            password,
        )


def add_user_to_identity(
    identity: Identity,
    *,
    email: str,
    role: Role,
    password: str = "test-password-123",
) -> Identity:
    with get_session_factory()() as session:
        user = User(email=email, name="Additional user", password_hash=hash_password(password))
        session.add(user)
        session.flush()
        membership = Membership(
            organization_id=identity.organization_id,
            user_id=user.id,
            role=role,
            business_id=identity.business_id,
        )
        session.add(membership)
        session.commit()
        return Identity(
            identity.organization_id,
            user.id,
            membership.id,
            identity.business_id,
            email,
            password,
        )


def login(client: TestClient, identity: Identity) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["membership"]["organization_id"] == str(identity.organization_id)
    assert client.cookies.get("growthos_session")
    assert client.cookies.get("growthos_csrf") == payload["csrf_token"]
    return payload["csrf_token"]


def csrf_headers(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}
