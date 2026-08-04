from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from growthos.client_ip import request_client_ip
from growthos.config import Settings

_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, settings: Settings, logger: logging.Logger) -> None:
        super().__init__(app)
        self._settings = settings
        self._logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _safe_request_id(request.headers.get("x-request-id"))
        client_ip = request_client_ip(request, self._settings)
        request.state.request_id = request_id
        request.state.client_ip = client_ip
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self._logger.exception(
                "http request failed",
                extra=_log_context(request, request_id, client_ip, 500, started),
            )
            raise
        response.headers["X-Request-ID"] = request_id
        self._logger.info(
            "http request completed",
            extra=_log_context(
                request,
                request_id,
                client_ip,
                response.status_code,
                started,
            ),
        )
        return response


def _safe_request_id(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized if _REQUEST_ID.fullmatch(normalized) else str(uuid4())


def _log_context(
    request: Request,
    request_id: str,
    client_ip: str,
    status_code: int,
    started: float,
) -> dict[str, object]:
    return {
        "event": "http.request",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "client_ip": client_ip,
    }
