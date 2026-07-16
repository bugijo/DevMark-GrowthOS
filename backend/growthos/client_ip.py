from __future__ import annotations

from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
    ip_network,
)
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from growthos.config import Settings

IPAddress = IPv4Address | IPv6Address
IPNetwork = IPv4Network | IPv6Network


def parse_trusted_proxy_cidrs(value: str) -> tuple[IPNetwork, ...]:
    return tuple(
        ip_network(item.strip(), strict=False) for item in value.split(",") if item.strip()
    )


def resolve_client_ip(
    peer_host: str,
    forwarded_for: str | None,
    *,
    trusted_proxy_cidrs: str,
) -> str:
    """Aceita X-Forwarded-For somente quando a borda imediata é confiável."""

    try:
        peer = ip_address(peer_host)
    except ValueError:
        return peer_host or "unknown"
    trusted = parse_trusted_proxy_cidrs(trusted_proxy_cidrs)
    if not _is_trusted(peer, trusted) or not forwarded_for:
        return str(peer)

    raw_hops = [item.strip() for item in forwarded_for.split(",")]
    if not raw_hops or len(raw_hops) > 20 or any(not item for item in raw_hops):
        return str(peer)
    try:
        hops = [ip_address(item) for item in raw_hops]
    except ValueError:
        return str(peer)

    for hop in reversed(hops):
        if not _is_trusted(hop, trusted):
            return str(hop)
    return str(hops[0])


def request_client_ip(request: Request, settings: Settings) -> str:
    peer_host = request.client.host if request.client is not None else "unknown"
    return resolve_client_ip(
        peer_host,
        request.headers.get("x-forwarded-for"),
        trusted_proxy_cidrs=settings.trusted_proxy_cidrs,
    )


def _is_trusted(address: IPAddress, networks: tuple[IPNetwork, ...]) -> bool:
    return any(address.version == network.version and address in network for network in networks)
