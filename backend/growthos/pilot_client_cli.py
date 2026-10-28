"""Provisiona o usuário demonstrativo do responsável por um negócio piloto.

Uso (dentro do contêiner do backend, nunca em produção):
    growthos-pilot-client --org devmark-demo --business "Villa Pet"

Cria (ou reaproveita) um usuário CLIENT_OWNER limitado ao negócio informado,
com e-mail e senha de demonstração vindos de DEMO_PILOT_CLIENT_EMAIL e
DEMO_PILOT_CLIENT_PASSWORD. Não envia convite nem e-mail.
"""

import argparse
import sys

from sqlalchemy import select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import Business, Membership, Organization, User
from growthos.security import hash_password, normalize_email
from growthos.services.audit import add_audit_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True, help="slug da organização")
    parser.add_argument("--business", required=True, help="nome exato do negócio")
    parser.add_argument("--name", default="Responsável (demonstração)")
    args = parser.parse_args(argv)

    settings = get_settings()
    if settings.app_env == "production":
        print("Usuário de demonstração não pode ser criado em produção", file=sys.stderr)
        return 2
    if len(settings.demo_pilot_client_password) < 12:
        print("DEMO_PILOT_CLIENT_PASSWORD deve ter ao menos 12 caracteres", file=sys.stderr)
        return 2

    with get_session_factory()() as session:
        organization = session.scalar(select(Organization).where(Organization.slug == args.org))
        if organization is None:
            print("Organização não encontrada", file=sys.stderr)
            return 1
        business = session.scalar(
            select(Business).where(
                Business.organization_id == organization.id, Business.name == args.business
            )
        )
        if business is None:
            print("Negócio não encontrado", file=sys.stderr)
            return 1
        email = normalize_email(settings.demo_pilot_client_email)
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                name=args.name,
                password_hash=hash_password(settings.demo_pilot_client_password),
                is_active=True,
            )
            session.add(user)
            session.flush()
        membership = session.scalar(
            select(Membership).where(
                Membership.organization_id == organization.id, Membership.user_id == user.id
            )
        )
        if membership is not None and (
            membership.role != Role.CLIENT_OWNER or membership.business_id != business.id
        ):
            print("Usuário já tem outro vínculo nesta organização; nada alterado", file=sys.stderr)
            return 1
        if membership is None:
            membership = Membership(
                organization_id=organization.id,
                user_id=user.id,
                role=Role.CLIENT_OWNER,
                business_id=business.id,
            )
            session.add(membership)
            session.flush()
            add_audit_log(
                session,
                organization_id=organization.id,
                business_id=business.id,
                actor_user_id=None,
                action="pilot_client.provisioned",
                resource_type="membership",
                resource_id=membership.id,
                details={"role": Role.CLIENT_OWNER.value, "demo": True},
            )
        session.commit()
        print(f"CLIENT_OWNER de {business.name}: {email}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
