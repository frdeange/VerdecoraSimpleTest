from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.upload_web.middleware.security_headers import SecurityHeadersMiddleware, normalize_storage_origin


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.mark.unit
def test_normalize_storage_origin_strips_path_and_trailing_slash() -> None:
    assert (
        normalize_storage_origin("https://stvdsdev4vtapr.blob.core.windows.net/upload-web-sas/")
        == "https://stvdsdev4vtapr.blob.core.windows.net"
    )


@pytest.mark.unit
def test_security_headers_middleware_reads_blob_origin_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_ACCOUNT_URL", "https://stvdsdev4vtapr.blob.core.windows.net/")

    with TestClient(_build_app(), base_url="https://testserver") as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert "connect-src 'self' https://stvdsdev4vtapr.blob.core.windows.net;" in response.headers[
        "Content-Security-Policy"
    ]
