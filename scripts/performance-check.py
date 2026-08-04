#!/usr/bin/env python3
"""Sonda local reproduzível; não envia dados para serviços externos."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


@dataclass(frozen=True, slots=True)
class Probe:
    label: str
    url: str


def require_local_url(value: str, label: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeError(f"{label} deve apontar para localhost")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(f"{label} não pode conter credencial")
    return value.rstrip("/")


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percent) - 1)]


def request_json(opener: Any, request: Request) -> Any:
    try:
        with opener.open(request, timeout=10) as response:
            payload = response.read()
    except HTTPError as exc:
        safe_body = exc.read(300).decode("utf-8", errors="replace")
        raise RuntimeError(
            f"HTTP {exc.code} em {request.full_url}: {safe_body}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"serviço indisponível em {request.full_url}") from exc
    return json.loads(payload) if payload else None


def measure(opener: Any, probe: Probe, iterations: int) -> tuple[list[float], int]:
    durations: list[float] = []
    response_bytes = 0
    for attempt in range(iterations + 1):
        started = time.perf_counter()
        try:
            with opener.open(Request(probe.url), timeout=10) as response:
                body = response.read()
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"HTTP {response.status} em {probe.url}")
        except (HTTPError, URLError) as exc:
            raise RuntimeError(
                f"falha ao medir {probe.label}: {type(exc).__name__}"
            ) from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        response_bytes = len(body)
        if attempt > 0:  # primeira chamada aquece conexões e caches locais
            durations.append(elapsed_ms)
    return durations, response_bytes


def directory_size(path: Path) -> int | None:
    if not path.exists():
        return None
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def compose_memory() -> list[str]:
    try:
        containers = subprocess.run(
            ["docker", "compose", "ps", "-q"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.split()
        if not containers:
            return ["stack Docker sem containers em execução"]
        output = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}}: {{.MemUsage}} ({{.MemPerc}})",
                *containers,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        return output.splitlines() or ["memória não informada pelo Docker"]
    except (FileNotFoundError, subprocess.SubprocessError):
        return ["memória não medida: Docker Compose indisponível"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Mede a stack local sem API externa.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("PERFORMANCE_API_URL", "http://localhost:8000/api/v1"),
    )
    parser.add_argument(
        "--frontend-url",
        default=os.getenv("PERFORMANCE_FRONTEND_URL", "http://localhost:3000"),
    )
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    if not 3 <= args.iterations <= 100:
        parser.error("--iterations deve estar entre 3 e 100")

    api_url = require_local_url(args.api_url, "--api-url")
    frontend_url = require_local_url(args.frontend_url, "--frontend-url")
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    login_payload = json.dumps(
        {
            "email": os.getenv("DEMO_ADMIN_EMAIL", "admin@devmark.local"),
            "password": os.getenv(
                "DEMO_ADMIN_PASSWORD", "local-demo-only-change-before-use"
            ),
        }
    ).encode()
    login = request_json(
        opener,
        Request(
            f"{api_url}/auth/login",
            data=login_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
    )
    if not isinstance(login, dict) or "user" not in login:
        raise RuntimeError("login demo não retornou o contrato esperado")
    businesses = request_json(opener, Request(f"{api_url}/businesses"))
    items = (
        businesses.get("items", businesses)
        if isinstance(businesses, dict)
        else businesses
    )
    business_id = items[0]["id"] if isinstance(items, list) and items else None
    today = datetime.now(UTC).date()
    period = f"starts_on={today.replace(day=1).isoformat()}&ends_on={today.isoformat()}"

    probes = [
        Probe("backend liveness", f"{api_url}/health/live"),
        Probe("sessão autenticada", f"{api_url}/auth/me"),
        Probe("lista de clientes", f"{api_url}/businesses"),
        Probe("lista de conteúdos", f"{api_url}/contents"),
        Probe("notificações", f"{api_url}/notifications"),
        Probe("frontend", frontend_url),
    ]
    if business_id:
        probes.append(
            Probe(
                "relatório do período",
                f"{api_url}/businesses/{business_id}/reports/period?{period}",
            )
        )

    print(f"Medição UTC: {datetime.now(UTC).isoformat()}")
    print(f"Amostras aquecidas por endpoint: {args.iterations}")
    print("Endpoint                         p50      p95      máx    resposta")
    failures: list[str] = []
    for probe in probes:
        durations, response_bytes = measure(opener, probe, args.iterations)
        p50 = statistics.median(durations)
        p95 = percentile(durations, 0.95)
        maximum = max(durations)
        print(
            f"{probe.label[:30]:30} {p50:7.1f}ms {p95:7.1f}ms "
            f"{maximum:7.1f}ms {response_bytes:8d} B"
        )
        limit = 200.0 if "liveness" in probe.label else 750.0
        if p95 > limit:
            failures.append(f"{probe.label}: p95 {p95:.1f} ms > {limit:.0f} ms")

    bundle_bytes = directory_size(Path("frontend/.next/static"))
    bundle_label = (
        f"{bundle_bytes / 1024 / 1024:.2f} MiB"
        if bundle_bytes is not None
        else "não medido (execute o build do frontend)"
    )
    print(f"\nArquivos estáticos do build: {bundle_label}")
    print("Memória dos containers:")
    for line in compose_memory():
        print(f"- {line}")
    if failures:
        print("Alertas de latência:")
        for failure in failures:
            print(f"- {failure}")
    return 1 if args.enforce and failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
