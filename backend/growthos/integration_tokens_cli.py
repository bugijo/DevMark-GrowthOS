"""Emite ou revoga credenciais de integração somente leitura.

Uso (dentro do contêiner do backend):
    growthos-integration-token issue --org devmark-demo --label hermes --days 30
    growthos-integration-token revoke --id <uuid>

`issue` imprime o token uma única vez em stdout (nada mais vai para stdout),
para que possa ser redirecionado direto a um arquivo protegido.
"""

import argparse
import sys
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.models import Organization
from growthos.services import integrations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    issue = commands.add_parser("issue")
    issue.add_argument("--org", required=True, help="slug da organização")
    issue.add_argument("--label", required=True)
    issue.add_argument("--days", type=int, default=30)
    issue.add_argument("--scope", action="append", default=None)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--id", required=True, type=UUID)
    args = parser.parse_args(argv)

    settings = get_settings()
    with get_session_factory()() as session:
        if args.command == "issue":
            organization = session.scalar(select(Organization).where(Organization.slug == args.org))
            if organization is None:
                print("Organização não encontrada", file=sys.stderr)
                return 1
            row, value = integrations.issue_integration_token(
                session,
                settings.effective_token_secret_key,
                organization,
                label=args.label,
                scopes=args.scope or [integrations.LEADS_READ],
                ttl=timedelta(days=args.days),
            )
            print(f"emitido id={row.id} expira={row.expires_at.isoformat()}", file=sys.stderr)
            print(value)
            return 0
        revoked = integrations.revoke_integration_token(session, args.id)
        if revoked is None:
            print("Credencial não encontrada", file=sys.stderr)
            return 1
        print(f"revogado id={revoked.id}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
