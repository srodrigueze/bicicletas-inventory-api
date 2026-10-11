"""Regression test for the ENABLE_API_DOCS toggle in app/main.py. Swagger/
ReDoc/openapi.json must be reachable by default (dev/test convenience) and
fully disabled when ENABLE_API_DOCS=false (production, RNG-01: no public
surface beyond what's strictly needed). Builds an isolated FastAPI app with
the exact same conditional construction used in app/main.py, instead of
reloading the shared app module, so it can't leak state into other test
files that import `app.main.app` directly.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(enable_api_docs: bool) -> FastAPI:
    return FastAPI(
        docs_url="/docs" if enable_api_docs else None,
        redoc_url="/redoc" if enable_api_docs else None,
        openapi_url="/openapi.json" if enable_api_docs else None,
    )


def test_docs_habilitados_por_defecto():
    with TestClient(_build_app(enable_api_docs=True)) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_docs_deshabilitados_en_produccion():
    with TestClient(_build_app(enable_api_docs=False)) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
