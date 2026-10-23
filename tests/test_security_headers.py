"""Security headers added by the middleware in app/main.py, and the storage
backend selection in app/api/deps.py.
"""

import pytest


def test_las_respuestas_llevan_cabeceras_de_seguridad(client):
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
    assert "max-age" in response.headers["Strict-Transport-Security"]


def test_las_respuestas_de_error_tambien_llevan_cabeceras(client):
    response = client.get("/bicycles/")

    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_storage_backend_no_soportado_falla_con_mensaje_claro(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, "storage_backend", "inexistente")
    deps.get_image_storage_repository.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="Unsupported STORAGE_BACKEND"):
            deps.get_image_storage_repository()
    finally:
        deps.get_image_storage_repository.cache_clear()
