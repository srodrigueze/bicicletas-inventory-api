"""Regression suite for the health check endpoint (GET /). No auth required:
this endpoint exists so any external monitor (uptime checker, Cloud Run
health probe, etc.) can confirm the API and its database connection are up.
"""


def test_health_check_ok_cuando_la_bd_responde(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_no_requiere_autenticacion(client):
    response = client.get("/")

    assert response.status_code != 401


def test_health_check_503_si_la_base_de_datos_no_responde(client, monkeypatch):
    from sqlmodel import Session

    def fake_execute(self, *args, **kwargs):
        raise Exception("simulated database outage")

    monkeypatch.setattr(Session, "execute", fake_execute)

    response = client.get("/")

    assert response.status_code == 503
