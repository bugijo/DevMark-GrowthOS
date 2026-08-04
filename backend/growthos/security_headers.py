from collections.abc import Mapping

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


def security_headers_for(environment: str, *, api_response: bool) -> Mapping[str, str]:
    headers = {
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-site",
        "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }
    if api_response:
        headers["Cache-Control"] = "no-store"
    if environment == "production":
        headers["Content-Security-Policy"] = (
            "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, environment: str, api_prefix: str) -> None:
        super().__init__(app)
        self._environment = environment
        self._api_prefix = api_prefix.rstrip("/") + "/"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = security_headers_for(
            self._environment,
            api_response=request.url.path.startswith(self._api_prefix),
        )
        for name, value in headers.items():
            if name not in response.headers:
                response.headers[name] = value
        return response
