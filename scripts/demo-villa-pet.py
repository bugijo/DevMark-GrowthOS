#!/usr/bin/env python3
"""Monta o piloto Villa Pet no stack local usando apenas APIs existentes.

Cria (se faltar) o cliente, o perfil de marca, a landing page em RASCUNHO e três
conteúdos de campanha pelo gerador mock. Não aprova a página: a aprovação é
humana, pela tela "Landing e interessados". Só aceita URLs locais, não envia
mensagens e não chama provedores pagos. Pode ser executado mais de uma vez.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT_DIR = Path(__file__).resolve().parent.parent
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
BUSINESS_NAME = "Villa Pet"

# Dados recebidos do cliente (docs/23-piloto-villa-pet.md). Preços são referência
# por porte e continuam sujeitos à confirmação final; sem pacotes nem descontos.
BRAND_PROFILE = {
    "brand_name": "Villa Pet",
    "public_name": "Villa Pet",
    "segment": "Pet shop — banho e tosa",
    "description": "Pet shop em Sertãozinho/SP com banho e tosa sob agendamento.",
    "audience": "Tutores de cães e gatos de Sertãozinho e região.",
    "tone_of_voice": "Acolhedor, claro e cuidadoso; sem promessas de resultado.",
    "services": ["Banho", "Banho e tosa"],
    "calls_to_action": ["Agendar banho e tosa"],
    "forbidden_rules": [
        "Não anunciar pacotes, descontos ou promoções não confirmados",
        "Não publicar preços antes da confirmação do responsável",
    ],
}
LANDING_PAGE = {
    "slug": "villa-pet",
    "headline": "Banho e tosa com cuidado, no horário combinado",
    "subheadline": (
        "Atendimento sob agendamento, com orientação conforme porte, pelagem e "
        "necessidade do seu pet."
    ),
    "cta_label": "Agendar banho e tosa",
    "address": "Rua Expedicionário Solano, 510 — Sertãozinho/SP",
    "contact_channel": "WhatsApp comercial (canal oficial a confirmar)",
    "highlights": [
        "Atendimento sob agendamento",
        "Orientação conforme porte e pelagem",
        "Confirmação de horário e preço antes do atendimento",
    ],
    "service_options": ["Banho", "Banho e tosa"],
    "price_items": [
        {"label": "Pequeno", "price_cents": 5500},
        {"label": "Médio", "price_cents": 7500},
        {"label": "Grande", "price_cents": 9500},
    ],
    "price_disclaimer": (
        "Valores de referência por porte, sujeitos à confirmação final da equipe "
        "conforme pelagem e necessidade do pet."
    ),
}
CAMPAIGN = [
    "Rotina de cuidado: convidar tutores a consultar banho e tosa sob agendamento",
    "Antes do atendimento: pedir porte, pelagem e última tosa para orientar o serviço",
    "Retorno de clientes: lembrar de programar o próximo cuidado com antecedência",
]


def require_local_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
        raise SystemExit("O roteiro aceita apenas URLs locais.")
    return value.rstrip("/")


def env_value(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name:
                return value.strip().strip("'\"")
    raise SystemExit(f"{name} não configurada.")


class Api:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.csrf = ""

    def call(
        self, method: str, path: str, body: Any = None, *, allow: set[int] = frozenset()
    ) -> Any:
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        if method != "GET" and self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        request = Request(
            self.base_url + path, data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.loads(response.read() or b"null")
        except HTTPError as exc:
            if exc.code in allow:
                return None
            detail = exc.read().decode(errors="replace")[:300]
            raise SystemExit(f"{method} {path} → HTTP {exc.code}: {detail}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--web", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    api = Api(require_local_url(args.api) + "/api/v1")
    web = require_local_url(args.web)

    login = api.call(
        "POST",
        "/auth/login",
        {
            "email": env_value("DEMO_ADMIN_EMAIL"),
            "password": env_value("DEMO_ADMIN_PASSWORD"),
        },
    )
    api.csrf = login["csrf_token"]

    listed = api.call("GET", "/businesses")
    items = (
        listed
        if isinstance(listed, list)
        else listed.get("items") or listed.get("data") or []
    )
    business = next((b for b in items if b["name"] == BUSINESS_NAME), None)
    if business is None:
        business = api.call(
            "POST",
            "/businesses",
            {"name": BUSINESS_NAME, "segment": BRAND_PROFILE["segment"]},
        )
        print(f"cliente criado: {business['id']}")
    else:
        print(f"cliente existente: {business['id']}")
    business_id = business["id"]

    if api.call("GET", f"/businesses/{business_id}/brand-profile", allow={404}) is None:
        api.call("PUT", f"/businesses/{business_id}/brand-profile", BRAND_PROFILE)
        print("perfil de marca: criado")
    else:
        print("perfil de marca: mantido")

    page = api.call("GET", f"/businesses/{business_id}/landing-page", allow={404})
    if page is None:
        page = api.call("PUT", f"/businesses/{business_id}/landing-page", LANDING_PAGE)
        print(f"landing: rascunho v{page['version']} criado")
    else:
        print(f"landing: mantida ({page['status']} v{page['version']})")

    contents = api.call("GET", f"/contents?business_id={business_id}&limit=100")
    if len(contents) >= len(CAMPAIGN):
        print(f"conteúdos de campanha: {len(contents)} existentes")
    else:
        for objective in CAMPAIGN[len(contents) :]:
            api.call(
                "POST",
                "/contents/generate",
                {
                    "business_id": business_id,
                    "objective": objective,
                    "channel": "INSTAGRAM",
                    "format": "FEED",
                    "notes": "Piloto Villa Pet; não publicar sem aprovação do responsável.",
                },
            )
        print(f"conteúdos de campanha: {len(CAMPAIGN) - len(contents)} gerados (mock)")

    print(f"\nPainel: {web}/landing  (revisar e aprovar a página)")
    print(f"Página após aprovação: {web}/p/{page['slug']}")
    print(f"Conteúdos para aprovação: {web}/conteudos")
    print("Nada foi publicado nem enviado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
