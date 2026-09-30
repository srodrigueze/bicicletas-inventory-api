"""Automated regression suite for DEV-004 (Auditoria). Each test below is
the automated version of one of the 14 test cases approved by the user
during DEV-004 — see `Desarrollo/DEV-004 - Auditoria.md` in the
documentation vault for the criteria/test-case definition and the
validation report.
"""

from datetime import date, timedelta

from sqlalchemy.exc import DBAPIError

from app.domain.entities.user import UserRole


def _admin_headers(make_user, token_for, document="1010144577"):
    make_user("Admin Test", document, UserRole.ADMINISTRADOR, is_superadmin=True)
    return token_for(document, document[-4:])


def _create_bicycle(client, headers, **overrides):
    payload = {
        "code": "B0001",
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


def _create_loan(client, headers, bicycle_ids, document="2000001"):
    payload = {
        "bicycle_ids": bicycle_ids,
        "client": {"full_name": "Juan Perez", "document": document, "phone": "3001234567"},
    }
    response = client.post("/loans/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _logs_for(client, headers, entity_name, action=None):
    logs = client.get("/audits/", headers=headers).json()
    matches = [log for log in logs if log["entity_name"] == entity_name]
    if action:
        matches = [log for log in matches if log["action"] == action]
    return matches


# --- Case 1: creating a user generates a CREATE audit log ------------------
def test_crear_usuario_genera_auditoria_create(client, make_user, token_for):
    headers = _admin_headers(make_user, token_for)

    response = client.post(
        "/users/",
        json={"full_name": "Nuevo Operador", "document": "3000000001", "status": "activo", "role": "operador"},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    matches = _logs_for(client, headers, "User", "create")
    assert any(log["entity_id"] == response.json()["id"] for log in matches)


# --- Case 2: editing a user generates an UPDATE audit log ------------------
def test_editar_usuario_genera_auditoria_update(client, make_user, token_for):
    headers = _admin_headers(make_user, token_for)
    created = client.post(
        "/users/",
        json={"full_name": "Editable", "document": "3000000002", "status": "activo", "role": "operador"},
        headers=headers,
    ).json()

    response = client.patch(f"/users/{created['id']}", json={"full_name": "Editado"}, headers=headers)
    assert response.status_code == 200, response.text

    matches = _logs_for(client, headers, "User", "update")
    assert any(log["entity_id"] == created["id"] for log in matches)


# --- Case 3: deactivating/reactivating a user generates DEACTIVATE/ACTIVATE
def test_desactivar_y_reactivar_usuario_genera_auditoria(client, make_user, token_for):
    headers = _admin_headers(make_user, token_for)
    created = client.post(
        "/users/",
        json={"full_name": "Toggle", "document": "3000000003", "status": "activo", "role": "operador"},
        headers=headers,
    ).json()

    client.patch(f"/users/{created['id']}", json={"status": "inactivo"}, headers=headers)
    client.patch(f"/users/{created['id']}", json={"status": "activo"}, headers=headers)

    matches = [log for log in _logs_for(client, headers, "User") if log["entity_id"] == created["id"]]
    actions = [log["action"] for log in matches]
    assert "deactivate" in actions
    assert "activate" in actions


# --- Case 4: creating a bicycle generates a CREATE audit log ---------------
def test_crear_bicicleta_genera_auditoria_create(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="A4")

    matches = _logs_for(client, auth_headers, "Bicycle", "create")
    assert any(log["entity_id"] == bicycle["id"] for log in matches)


# --- Case 5: editing a bicycle generates an UPDATE audit log ---------------
def test_editar_bicicleta_genera_auditoria_update(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="A5")

    client.patch(f"/bicycles/{bicycle['id']}", json={"observations": "Editada"}, headers=auth_headers)

    matches = _logs_for(client, auth_headers, "Bicycle", "update")
    assert any(log["entity_id"] == bicycle["id"] for log in matches)


# --- Case 6: deleting/restoring a bicycle generates DELETE/RESTORE ---------
def test_eliminar_y_restaurar_bicicleta_genera_auditoria(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="A6")

    client.delete(f"/bicycles/{bicycle['id']}", headers=auth_headers)
    client.patch(f"/bicycles/{bicycle['id']}/restore", headers=auth_headers)

    matches = [log for log in _logs_for(client, auth_headers, "Bicycle") if log["entity_id"] == bicycle["id"]]
    actions = [log["action"] for log in matches]
    assert "delete" in actions
    assert "restore" in actions


# --- Case 7: creating a loan generates a CREATE audit log on Loan ----------
def test_crear_prestamo_genera_auditoria_create(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="A7")
    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="3000000007")

    matches = _logs_for(client, auth_headers, "Loan", "create")
    assert any(log["entity_id"] == loan["id"] for log in matches)


# --- Case 8: adding a bicycle to an existing loan generates an ADD_BICYCLE
# audit log (replaces the removed swap action, 2026-09-28) -----------------
def test_agregar_bicicleta_genera_auditoria_add_bicycle(client, auth_headers):
    bike = _create_bicycle(client, auth_headers, code="A8A")
    extra_bike = _create_bicycle(client, auth_headers, code="A8B")
    loan = _create_loan(client, auth_headers, [bike["id"]], document="3000000008")

    client.post(
        f"/loans/{loan['id']}/details",
        json={"bicycle_ids": [extra_bike["id"]]},
        headers=auth_headers,
    )

    matches = _logs_for(client, auth_headers, "Loan", "add_bicycle")
    assert any(log["entity_id"] == loan["id"] for log in matches)


# --- Case 9: returning a detail generates a RETURNED audit log -------------
def test_devolucion_genera_auditoria_returned(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="A9")
    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="3000000009")
    detail_id = loan["details"][0]["id"]

    client.post(f"/loans/{loan['id']}/details/{detail_id}/return", headers=auth_headers)

    matches = _logs_for(client, auth_headers, "Loan", "returned")
    assert any(log["entity_id"] == loan["id"] for log in matches)


# --- Case 10: GET /audits/ works for an authenticated operador -------------
def test_audits_accesible_para_operador(client, auth_headers):
    response = client.get("/audits/", headers=auth_headers)

    assert response.status_code == 200


# --- Case 11: GET /audits/ without a token is rejected ---------------------
def test_audits_sin_token_es_rechazado(client):
    response = client.get("/audits/")

    assert response.status_code == 401


# --- Case 12: bicycles/loans/clients endpoints without a token are 401 ----
def test_clients_sin_token_es_rechazado(client):
    response = client.get("/clients/by-document/1234567")

    assert response.status_code == 401


# --- Case 13: the audit log listing is paginated ---------------------------
def test_listado_de_auditorias_paginado(client, auth_headers):
    _create_bicycle(client, auth_headers, code="A13A")
    _create_bicycle(client, auth_headers, code="A13B")

    first_page = client.get("/audits/?skip=0&limit=1", headers=auth_headers)
    second_page = client.get("/audits/?skip=1&limit=1", headers=auth_headers)

    assert first_page.status_code == 200
    assert len(first_page.json()) == 1
    assert second_page.status_code == 200
    assert len(second_page.json()) == 1
    assert first_page.json()[0]["id"] != second_page.json()[0]["id"]


# --- Case 14: a direct UPDATE/DELETE against audit_log fails via trigger --
def test_audit_log_es_inmutable_a_nivel_de_base_de_datos(client, auth_headers, db_session):
    from sqlalchemy import text

    _create_bicycle(client, auth_headers, code="A14")

    session = db_session
    try:
        session.execute(text("UPDATE audit_log SET entity_id = entity_id"))
        session.commit()
        assert False, "expected the trigger to reject the UPDATE"
    except DBAPIError:
        session.rollback()

    try:
        session.execute(text("DELETE FROM audit_log"))
        session.commit()
        assert False, "expected the trigger to reject the DELETE"
    except DBAPIError:
        session.rollback()


# --- Case 15: filtering by a single date includes only that day's logs -----
def test_auditorias_filtradas_por_un_solo_dia(client, auth_headers):
    _create_bicycle(client, auth_headers, code="A15")
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    today_logs = client.get(f"/audits/?start_date={today}", headers=auth_headers).json()
    yesterday_logs = client.get(
        f"/audits/?start_date={yesterday}&end_date={yesterday}", headers=auth_headers
    ).json()

    assert any(log["entity_name"] == "Bicycle" for log in today_logs)
    assert yesterday_logs == []


# --- Case 16: filtering by a date range -------------------------------------
def test_auditorias_filtradas_por_rango_de_fechas(client, auth_headers):
    _create_bicycle(client, auth_headers, code="A16")
    start = (date.today() - timedelta(days=1)).isoformat()
    end = date.today().isoformat()

    logs = client.get(f"/audits/?start_date={start}&end_date={end}", headers=auth_headers).json()

    assert any(log["entity_name"] == "Bicycle" for log in logs)


# --- Case 17: an inverted range (start after end) is rejected --------------
def test_auditorias_rango_invertido_es_rechazado(client, auth_headers):
    today = date.today()
    yesterday = today - timedelta(days=1)

    response = client.get(
        f"/audits/?start_date={today.isoformat()}&end_date={yesterday.isoformat()}", headers=auth_headers
    )

    assert response.status_code == 422


# --- Case 18: filtering by user_id returns only that user's own actions ----
def test_auditorias_filtradas_por_usuario(client, make_user, token_for):
    admin_headers = _admin_headers(make_user, token_for, document="1010144578")
    second_admin_headers = _admin_headers(make_user, token_for, document="1010144579")

    created_by_admin = client.post(
        "/users/",
        json={"full_name": "Por Admin 1", "document": "3000000098", "status": "activo", "role": "operador"},
        headers=admin_headers,
    ).json()
    created_by_second = client.post(
        "/users/",
        json={"full_name": "Por Admin 2", "document": "3000000099", "status": "activo", "role": "operador"},
        headers=second_admin_headers,
    ).json()

    admin_id = client.get("/users/me", headers=admin_headers).json()["id"]

    logs = client.get(f"/audits/?user_id={admin_id}", headers=admin_headers).json()

    assert all(log["user_id"] == admin_id for log in logs)
    assert any(log["entity_id"] == created_by_admin["id"] for log in logs)
    assert not any(log["entity_id"] == created_by_second["id"] for log in logs)


# --- Case 19: filtering by entity_name returns only logs for that entity ---
def test_auditorias_filtradas_por_entidad(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="A19")
    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="4000000001")

    bicycle_logs = client.get("/audits/?entity_name=Bicycle", headers=auth_headers).json()
    loan_logs = client.get("/audits/?entity_name=Loan", headers=auth_headers).json()

    assert all(log["entity_name"] == "Bicycle" for log in bicycle_logs)
    assert any(log["entity_id"] == bicycle["id"] for log in bicycle_logs)
    assert all(log["entity_name"] == "Loan" for log in loan_logs)
    assert any(log["entity_id"] == loan["id"] for log in loan_logs)
