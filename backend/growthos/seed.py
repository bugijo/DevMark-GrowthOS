import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import BrandProfile, Business, Membership, Organization, User
from growthos.security import hash_password, normalize_email


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "devmark-demo"


def _get_or_create_user(session: Session, email: str, name: str, password: str) -> User:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None:
        user = User(
            email=normalized,
            name=name,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        session.flush()
    return user


def seed_demo(session: Session) -> dict[str, UUID]:
    settings = get_settings()
    settings.ensure_demo_seed_allowed()
    slug = _slugify(settings.demo_organization_name)
    organization = session.scalar(select(Organization).where(Organization.slug == slug))
    if organization is None:
        organization = Organization(name=settings.demo_organization_name, slug=slug)
        session.add(organization)
        session.flush()

    business = session.scalar(
        select(Business).where(
            Business.organization_id == organization.id,
            Business.name == "Clínica Veterinária Demo",
        )
    )
    if business is None:
        business = Business(
            organization_id=organization.id,
            name="Clínica Veterinária Demo",
            segment="Clínica veterinária",
        )
        session.add(business)
        session.flush()

    admin = _get_or_create_user(
        session,
        settings.demo_admin_email,
        "Administrador DevMark Demo",
        settings.demo_admin_password,
    )
    reviewer = _get_or_create_user(
        session,
        settings.demo_client_email,
        "Revisor Cliente Demo",
        settings.demo_client_password,
    )

    memberships = [
        (admin, Role.AGENCY_ADMIN, None),
        (reviewer, Role.CLIENT_REVIEWER, business.id),
    ]
    for user, role, business_id in memberships:
        membership = session.scalar(
            select(Membership).where(
                Membership.organization_id == organization.id,
                Membership.user_id == user.id,
            )
        )
        if membership is None:
            session.add(
                Membership(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=role,
                    business_id=business_id,
                )
            )

    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    if brand is None:
        session.add(
            BrandProfile(
                organization_id=organization.id,
                business_id=business.id,
                brand_name="Clínica Veterinária Demo",
                public_name="Vet Demo",
                description="Dados inteiramente fictícios para desenvolvimento local.",
                segment="Clínica veterinária",
                audience="Tutores de animais da região",
                primary_colors=["#1F7A6D", "#F4F1DE"],
                tone_of_voice="acolhedor, claro e responsável",
                calls_to_action=["Agende uma conversa com nossa equipe."],
            )
        )
    session.commit()
    return {
        "organization_id": organization.id,
        "business_id": business.id,
        "admin_user_id": admin.id,
        "reviewer_user_id": reviewer.id,
    }


def main() -> None:
    with get_session_factory()() as session:
        result = seed_demo(session)
    print("Seed demo concluído:", result)


if __name__ == "__main__":
    main()
