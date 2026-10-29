"""Cria um kit demonstrativo de cliente para uma organização de agência.

Uso (fora de produção):
    growthos-client-kit --org agencia-demo ./cliente.json

O JSON deve conter ``name``, ``segment`` e ``slug``. O kit deixa a landing
privada, sem preços e sem WhatsApp, para confirmação posterior do responsável.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.models import Business, LandingPage, Organization
from growthos.services.audit import add_audit_log


def _read_input(path: Path) -> tuple[str, str, str]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("o JSON deve conter um objeto")
    values: list[str] = []
    for field in ("name", "segment", "slug"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"campo obrigatório inválido: {field}")
        values.append(value.strip())
    return values[0], values[1], values[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True, help="slug da organização da agência")
    parser.add_argument("input_path", nargs="?", type=Path, help="arquivo JSON do novo cliente")
    parser.add_argument("--input", dest="input_option", type=Path, help="arquivo JSON do novo cliente")
    args = parser.parse_args(argv)

    if os.getenv("APP_ENV", "").strip().casefold() == "production":
        print("Kit demonstrativo de cliente não pode ser criado em produção", file=sys.stderr)
        return 2
    settings = get_settings()
    if settings.app_env == "production":
        print("Kit demonstrativo de cliente não pode ser criado em produção", file=sys.stderr)
        return 2

    input_path = args.input_option or args.input_path
    if input_path is None:
        parser.error("informe o arquivo JSON")
    try:
        name, segment, slug = _read_input(input_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Entrada inválida: {exc}", file=sys.stderr)
        return 2

    with get_session_factory()() as session:
        organization = session.scalar(select(Organization).where(Organization.slug == args.org))
        if organization is None:
            print("Organização não encontrada", file=sys.stderr)
            return 1

        business = session.scalar(
            select(Business).where(
                Business.organization_id == organization.id,
                Business.name == name,
            )
        )
        provisioned = False
        if business is None:
            business = Business(
                organization_id=organization.id,
                name=name,
                segment=segment,
            )
            session.add(business)
            session.flush()
            provisioned = True

        landing = session.scalar(
            select(LandingPage).where(LandingPage.business_id == business.id)
        )
        if landing is None:
            slug_owner = session.scalar(select(LandingPage).where(LandingPage.slug == slug))
            if slug_owner is not None and slug_owner.business_id != business.id:
                print("Slug da landing já está em uso", file=sys.stderr)
                return 1
            landing = LandingPage(
                organization_id=organization.id,
                business_id=business.id,
                slug=slug,
                status="DRAFT",
                headline=f"Conheça {name}",
                subheadline=f"Informações iniciais sobre {segment.lower()}.",
                cta_label="Saiba mais",
                whatsapp_number="",
                price_items=[],
                demo_mode=True,
            )
            session.add(landing)
            session.flush()
            provisioned = True

        if provisioned:
            add_audit_log(
                session,
                organization_id=organization.id,
                business_id=business.id,
                actor_user_id=None,
                action="client_kit.provisioned",
                resource_type="landing_page",
                resource_id=landing.id,
                details={"demo": True, "status": "DRAFT"},
            )
        session.commit()
        result = "criado" if provisioned else "já existente"
        print(f"Kit demonstrativo {result}: {name} ({landing.slug})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
