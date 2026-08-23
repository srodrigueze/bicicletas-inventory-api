"""Automated regression suite for DEV-005 (Reportes en PDF). Each test below
is the automated version of one of the test cases approved by the user during
DEV-005 — see `Desarrollo/DEV-005 - Reportes en PDF.md` in the documentation
vault for the criteria/test-case definition and the validation report.
"""

from datetime import date, timedelta

from app.domain.entities.user import UserRole


def _admin_headers(make_user, token_for, document="4000000001"):
    make_user("Admin Reportes", document, UserRole.ADMINISTRADOR, is_superadmin=True)
    return token_for(document, document[-4:])


def _create_bicycle(client, headers, **overrides):
    payload = {
        "code": "R0001",
        "condition": "good",
        "size": "medium",
        "rueditas_asistencia": False,
        "tiene_pedales": True,
        "observations": None,
    }
    payload.update(overrides)
    response = client.post("/bicycles/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_loan(client, headers, bicycle_ids, document="5000001"):
    payload = {
        "bicycle_ids": bicycle_ids,
        "client": {"full_name": "Cliente Reporte", "document": document, "phone": "3009998877"},
    }
    response = client.post("/loans/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# --- Case 1: admin gets a PDF for a range that includes a loan -------------
def test_reporte_incluye_prestamos_del_rango(client, auth_headers, make_user, token_for):
    admin_headers = _admin_headers(make_user, token_for)
    bicycle = _create_bicycle(client, auth_headers, code="R0001")
    _create_loan(client, auth_headers, [bicycle["id"]], document="5000001")

    today = date.today().isoformat()
    response = client.get(f"/reports/loans?start_date={today}&end_date={today}", headers=admin_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


# --- Case 2: an empty range still returns a valid PDF -----------------------
def test_reporte_sin_prestamos_genera_pdf_valido(client, make_user, token_for):
    admin_headers = _admin_headers(make_user, token_for, document="4000000002")
    past_day = (date.today() - timedelta(days=365)).isoformat()

    response = client.get(f"/reports/loans?start_date={past_day}&end_date={past_day}", headers=admin_headers)

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


# --- Case 3: an operator cannot generate the report -------------------------
def test_operador_no_puede_generar_reporte(client, auth_headers):
    today = date.today().isoformat()

    response = client.get(f"/reports/loans?start_date={today}&end_date={today}", headers=auth_headers)

    assert response.status_code == 403


# --- Case 4: without a token the endpoint is rejected -----------------------
def test_reporte_sin_token_es_rechazado(client):
    today = date.today().isoformat()

    response = client.get(f"/reports/loans?start_date={today}&end_date={today}")

    assert response.status_code == 401


# --- Case 5: start_date after end_date is rejected --------------------------
def test_rango_invertido_es_rechazado(client, make_user, token_for):
    admin_headers = _admin_headers(make_user, token_for, document="4000000003")
    today = date.today()
    yesterday = today - timedelta(days=1)

    response = client.get(
        f"/reports/loans?start_date={today.isoformat()}&end_date={yesterday.isoformat()}",
        headers=admin_headers,
    )

    assert response.status_code == 422


# --- Case 6: a loan outside the range is excluded ---------------------------
def test_prestamo_fuera_de_rango_no_aparece(client, auth_headers, make_user, token_for):
    admin_headers = _admin_headers(make_user, token_for, document="4000000004")
    bicycle = _create_bicycle(client, auth_headers, code="R0002")
    _create_loan(client, auth_headers, [bicycle["id"]], document="5000002")

    today = date.today().isoformat()
    future_day = (date.today() + timedelta(days=30)).isoformat()

    in_range = client.get(f"/reports/loans?start_date={today}&end_date={today}", headers=admin_headers)
    out_of_range = client.get(f"/reports/loans?start_date={future_day}&end_date={future_day}", headers=admin_headers)

    assert in_range.status_code == 200 and out_of_range.status_code == 200
    # PDF content streams are compressed, so the bicycle code isn't searchable
    # as plain bytes; compare sizes instead — the in-range report renders a
    # full loan table while the out-of-range one only renders the "no
    # results" paragraph, so it must be meaningfully smaller.
    assert len(out_of_range.content) < len(in_range.content)
