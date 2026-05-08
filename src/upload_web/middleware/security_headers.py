"""Strict security headers middleware for Upload Web (#119).

Adds CSP, HSTS, X-Content-Type-Options, X-Frame-Options and
Referrer-Policy to every response. The CSP is tuned to allow HTMX
(inline scripts via nonce are NOT required because HTMX uses
``unsafe-inline`` for hx-* attributes).
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.upload_web.config import UploadWebSettings

DEFAULT_STORAGE_ACCOUNT_URL = str(UploadWebSettings.model_fields["blob_account"].default or "")

_BASE_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def normalize_storage_origin(storage_account_url: str | None) -> str:
    """Return only the origin portion of a configured storage account URL."""
    if storage_account_url is None:
        return ""

    raw_value = storage_account_url.strip()
    if not raw_value or raw_value == DEFAULT_STORAGE_ACCOUNT_URL:
        return ""
    if "://" not in raw_value:
        raw_value = f"https://{raw_value}"

    parsed = urlsplit(raw_value)
    if not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def build_content_security_policy(storage_account_url: str | None = None) -> str:
    """Build the CSP with the Blob Storage origin included in connect-src."""
    storage_origin = normalize_storage_origin(storage_account_url)
    connect_sources = ["'self'"]
    if storage_origin:
        connect_sources.append(storage_origin)

    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        f"connect-src {' '.join(connect_sources)}; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self' https://login.microsoftonline.com"
    )


def build_security_headers(storage_account_url: str | None = None) -> dict[str, str]:
    """Build the full security headers set for Upload Web responses."""
    return {
        **_BASE_HEADERS,
        "Content-Security-Policy": build_content_security_policy(storage_account_url),
    }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security headers to every HTTP response."""

    def __init__(self, app: Any, *, storage_account_url: str | None = None, **kwargs: Any) -> None:
        super().__init__(app, **kwargs)
        resolved_storage_account_url = (
            storage_account_url
            or os.getenv("STORAGE_ACCOUNT_URL")
            or os.getenv("BLOB_ACCOUNT")
        )
        self._security_headers = build_security_headers(resolved_storage_account_url)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for name, value in self._security_headers.items():
            response.headers.setdefault(name, value)
        return response
