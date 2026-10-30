#!/usr/bin/env python3
"""Percorre o pipeline comercial no stack local com um lead fictício.

Fluxo: lead → contato → briefing → proposta (rascunho não enviado) → tarefa de
acompanhamento. Somente URLs locais; nenhuma mensagem, e-mail ou proposta é
enviada. As credenciais demo são lidas do ambiente ou do `.env` e nunca são
impressas.
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

# Cenário de demonstração: o negócio é o piloto Villa Pet, mas contato, e-mail e
# telefone são fictícios. Os preços abaixo são referências recebidas por porte
# e permanecem pendentes de confirmação pelo responsável.
VILLA_PET_DEMO_LEAD = {
    "name": "Contato Demonstração",
    "company": "Villa Pet (demonstração)",
    "email": "contato.villapet@example.test",
    "business_type": "Pet shop — banho e tosa",
    "goal": (
        "Landing page para pedidos de banho e tosa sob agendamento, com CTA para "
        "o WhatsApp comercial e registro da origem do contato"
    ),
    "desired_timeline": "Piloto após aprovação do responsável",
    "additional_info": (
        "DADOS FICTÍCIOS. Referência por porte a confirmar: pequeno R$ 55, "
        "médio R$ 75, grande R$ 95. Pacotes e descontos não definidos."
    ),
}


def require_local_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
        raise SystemExit("A demonstração aceita apenas URLs locais.")
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
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.csrf = ""

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
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
            with self.opener.open(request, timeout=15) as response:
                return json.loads(response.read() or b"null")
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise SystemExit(f"{method} {path} → HTTP {exc.code}: {detail}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    api = Api(require_local_url(args.api))

    login = api.call(
        "POST",
        "/api/v1/auth/login",
        {
            "email": env_value("DEMO_ADMIN_EMAIL"),
            "password": env_value("DEMO_ADMIN_PASSWORD"),
        },
    )
    api.csrf = login["csrf_token"]
    print(f"login: ok (organização {login['organization']['slug']})")

    lead = api.call("POST", "/api/v1/sales/leads", VILLA_PET_DEMO_LEAD)
    lead_id = lead["id"]
    print(
        f"lead: {lead_id} stage={lead['stage']} classificação={lead['service_classification']}"
    )

    for stage in ("CONTACT_PENDING", "BRIEFING"):
        moved = api.call(
            "PATCH", f"/api/v1/sales/leads/{lead_id}/stage", {"stage": stage}
        )
        print(f"etapa: {moved['stage']}")

    briefing = api.call("GET", f"/api/v1/sales/leads/{lead_id}/briefing")
    print(f"briefing: ai_used={briefing['ai_used']}")

    proposal = api.call("POST", f"/api/v1/sales/leads/{lead_id}/proposal-draft")
    if proposal["status"] != "DRAFT_NOT_SENT":
        raise SystemExit("A proposta deveria permanecer como rascunho não enviado.")
    print(f"proposta: {proposal['status']} ai_used={proposal['ai_used']}")

    task = api.call(
        "POST",
        f"/api/v1/sales/leads/{lead_id}/tasks",
        {
            "title": "Confirmar preços e aprovação com a Villa Pet",
            "notes": "Exercício fictício; não contatar ninguém a partir desta tarefa.",
        },
    )
    print(f"acompanhamento: tarefa {task['id']}")
    print("Concluído. Nada foi enviado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
