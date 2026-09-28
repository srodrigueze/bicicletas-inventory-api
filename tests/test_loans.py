"""Automated regression suite for DEV-003 (Prestamos y clientes). Each test
below is the automated version of one of the 13 test cases approved by the
user during DEV-003 — see `Desarrollo/DEV-003 - Prestamos y clientes.md` in
the documentation vault for the criteria/test-case definition and the
validation report.

Since DEV-004 added JWT protection to the loans endpoints, every request
here goes through `auth_headers` (an authenticated operador).
"""


def _create_bicycle(client, auth_headers, **overrides):
    payload = {
        "code": "B0001",
        "condition": "good",
        "size": "medium",
        "rueditas_asistencia": False,
        "tiene_pedales": True,
        "observations": None,
    }
    payload.update(overrides)
    response = client.post("/bicycles/", json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def _client_payload(**overrides):
    payload = {"full_name": "Juan Perez", "document": "1000001", "phone": "3001234567"}
    payload.update(overrides)
    return payload


def _create_loan(client, auth_headers, bicycle_ids, **client_overrides):
    payload = {"bicycle_ids": bicycle_ids, "client": _client_payload(**client_overrides)}
    response = client.post("/loans/", json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


# --- Case 1: creating a new client while registering a loan -----------------
def test_crear_cliente_nuevo_al_registrar_prestamo(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L1")

    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="2000001")

    assert loan["client"]["document"] == "2000001"
    assert loan["client"]["full_name"] == "Juan Perez"


# --- Case 2: reusing an existing client by document (autocomplete) ---------
def test_reutilizar_cliente_existente_por_documento(client, auth_headers):
    bike_a = _create_bicycle(client, auth_headers, code="L2A")
    bike_b = _create_bicycle(client, auth_headers, code="L2B")

    first_loan = _create_loan(client, auth_headers, [bike_a["id"]], document="2000002", full_name="Ana Gomez")
    second_loan = _create_loan(client, auth_headers, [bike_b["id"]], document="2000002", full_name="Ana Gomez")

    assert first_loan["client"]["id"] == second_loan["client"]["id"]
    assert second_loan["client"]["full_name"] == "Ana Gomez"


# --- Case 2b: registering a loan for an existing client with different data
# updates the stored client record instead of keeping the stale data --------
def test_datos_de_cliente_distintos_actualizan_el_registro_existente(client, auth_headers):
    bike_a = _create_bicycle(client, auth_headers, code="L2C")
    bike_b = _create_bicycle(client, auth_headers, code="L2D")

    first_loan = _create_loan(
        client, auth_headers, [bike_a["id"]], document="2000018", full_name="Ana Gomez", phone="3000000000"
    )
    second_loan = _create_loan(
        client, auth_headers, [bike_b["id"]], document="2000018", full_name="Ana G. Ramirez", phone="3111111111"
    )

    assert first_loan["client"]["id"] == second_loan["client"]["id"]
    assert second_loan["client"]["full_name"] == "Ana G. Ramirez"
    assert second_loan["client"]["phone"] == "3111111111"

    by_document = client.get("/clients/by-document/2000018", headers=auth_headers)
    assert by_document.json()["full_name"] == "Ana G. Ramirez"
    assert by_document.json()["phone"] == "3111111111"


# --- Case 3: client document out of range (5 or 15 chars) is rejected ------
def test_documento_cliente_fuera_de_rango_es_rechazado(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L3")

    too_short = client.post(
        "/loans/",
        json={"bicycle_ids": [bicycle["id"]], "client": _client_payload(document="12345")},
        headers=auth_headers,
    )
    too_long = client.post(
        "/loans/",
        json={"bicycle_ids": [bicycle["id"]], "client": _client_payload(document="123456789012345")},
        headers=auth_headers,
    )

    assert too_short.status_code == 422
    assert too_long.status_code == 422


# --- Case 4: client document with letters is accepted ----------------------
def test_documento_cliente_con_letras_es_aceptado(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L4")

    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="CC123456")

    assert loan["client"]["document"] == "CC123456"


# --- Case 5: a loan with multiple bicycles in a single creation ------------
def test_prestamo_con_multiples_bicicletas(client, auth_headers):
    bike_a = _create_bicycle(client, auth_headers, code="L5A")
    bike_b = _create_bicycle(client, auth_headers, code="L5B")

    loan = _create_loan(client, auth_headers, [bike_a["id"], bike_b["id"]], document="2000005")

    assert len(loan["details"]) == 2
    assert {d["bicycle_id"] for d in loan["details"]} == {bike_a["id"], bike_b["id"]}
    assert all(d["status"] == "on_loan" for d in loan["details"])


# --- Case 6: a bicycle needing repairs can be loaned ------------------------
def test_bicicleta_necesita_reparaciones_puede_prestarse(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L6", condition="bad")

    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="2000006")

    assert loan["details"][0]["bicycle_id"] == bicycle["id"]


# --- Case 7: a bicycle not in possession of the JAC cannot be loaned -------
def test_bicicleta_fuera_de_posesion_no_puede_prestarse(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L7")
    client.delete(f"/bicycles/{bicycle['id']}", headers=auth_headers)

    response = client.post(
        "/loans/",
        json={"bicycle_ids": [bicycle["id"]], "client": _client_payload(document="2000007")},
        headers=auth_headers,
    )

    assert response.status_code == 409


# --- Case 8: a bicycle with an active loan cannot be reassigned ------------
def test_bicicleta_con_prestamo_activo_no_se_reasigna(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L8")
    _create_loan(client, auth_headers, [bicycle["id"]], document="2000008")

    response = client.post(
        "/loans/",
        json={"bicycle_ids": [bicycle["id"]], "client": _client_payload(document="2000009")},
        headers=auth_headers,
    )

    assert response.status_code == 409


# --- Case 9: returning a detail marks it returned with returned_at and -----
# frees the bicycle for a new loan
def test_devolver_linea_marca_entregada_y_libera_bicicleta(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L9")
    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="2000010")
    detail_id = loan["details"][0]["id"]

    returned = client.post(f"/loans/{loan['id']}/details/{detail_id}/return", headers=auth_headers)

    assert returned.status_code == 200, returned.text
    body = returned.json()
    assert body["details"][0]["status"] == "returned"
    assert body["details"][0]["returned_at"] is not None

    new_loan = _create_loan(client, auth_headers, [bicycle["id"]], document="2000011")
    assert new_loan["details"][0]["bicycle_id"] == bicycle["id"]


# --- Case 10: a loan with all details returned is no longer active --------
def test_prestamo_con_todas_las_lineas_entregadas_deja_de_ser_activo(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="L10")
    loan = _create_loan(client, auth_headers, [bicycle["id"]], document="2000012")
    detail_id = loan["details"][0]["id"]

    client.post(f"/loans/{loan['id']}/details/{detail_id}/return", headers=auth_headers)

    active_list = client.get("/loans/?active_only=true", headers=auth_headers)
    full_list = client.get("/loans/?active_only=false", headers=auth_headers)

    assert loan["id"] not in [item["id"] for item in active_list.json()]
    assert loan["id"] in [item["id"] for item in full_list.json()]


# --- Case 11: changing a bicycle is now "return one, then add another" ----
# under the same loan_id, not a single swap operation ------------------------
def test_cambiar_bicicleta_es_devolver_y_agregar_bajo_el_mismo_prestamo(client, auth_headers):
    old_bike = _create_bicycle(client, auth_headers, code="L11A")
    new_bike = _create_bicycle(client, auth_headers, code="L11B")
    loan = _create_loan(client, auth_headers, [old_bike["id"]], document="2000013")
    old_detail_id = loan["details"][0]["id"]

    client.post(f"/loans/{loan['id']}/details/{old_detail_id}/return", headers=auth_headers)
    added = client.post(
        f"/loans/{loan['id']}/details",
        json={"bicycle_ids": [new_bike["id"]]},
        headers=auth_headers,
    )

    assert added.status_code == 200, added.text
    body = added.json()
    assert body["id"] == loan["id"]
    statuses_by_bike = {d["bicycle_id"]: d["status"] for d in body["details"]}
    assert statuses_by_bike[old_bike["id"]] == "returned"
    assert statuses_by_bike[new_bike["id"]] == "on_loan"


# --- Case 14: a client with an active loan can get more bicycles added to --
# the SAME loan, without returning the ones they already have --------------
def test_agregar_bicicletas_a_prestamo_activo_sin_devolver_las_anteriores(client, auth_headers):
    bike_a = _create_bicycle(client, auth_headers, code="L14A")
    bike_b = _create_bicycle(client, auth_headers, code="L14B")
    loan = _create_loan(client, auth_headers, [bike_a["id"]], document="2000019")

    response = client.post(
        f"/loans/{loan['id']}/details",
        json={"bicycle_ids": [bike_b["id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == loan["id"]
    statuses_by_bike = {d["bicycle_id"]: d["status"] for d in body["details"]}
    assert statuses_by_bike[bike_a["id"]] == "on_loan"
    assert statuses_by_bike[bike_b["id"]] == "on_loan"


# --- Case 15: adding an unavailable bicycle to a loan is rejected ----------
def test_agregar_bicicleta_no_disponible_es_rechazado(client, auth_headers):
    bike_a = _create_bicycle(client, auth_headers, code="L15A")
    taken_bike = _create_bicycle(client, auth_headers, code="L15B")
    loan = _create_loan(client, auth_headers, [bike_a["id"]], document="2000020")
    _create_loan(client, auth_headers, [taken_bike["id"]], document="2000021")

    response = client.post(
        f"/loans/{loan['id']}/details",
        json={"bicycle_ids": [taken_bike["id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 409


# --- Case 12: the default listing shows only active loans, filter toggles -
# to see all
def test_listado_por_defecto_solo_activos(client, auth_headers):
    bike_active = _create_bicycle(client, auth_headers, code="L12A")
    bike_returned = _create_bicycle(client, auth_headers, code="L12B")
    active_loan = _create_loan(client, auth_headers, [bike_active["id"]], document="2000014")
    returned_loan = _create_loan(client, auth_headers, [bike_returned["id"]], document="2000015")
    client.post(
        f"/loans/{returned_loan['id']}/details/{returned_loan['details'][0]['id']}/return",
        headers=auth_headers,
    )

    default_list = client.get("/loans/", headers=auth_headers)
    full_list = client.get("/loans/?active_only=false", headers=auth_headers)

    default_ids = [item["id"] for item in default_list.json()]
    full_ids = [item["id"] for item in full_list.json()]
    assert active_loan["id"] in default_ids
    assert returned_loan["id"] not in default_ids
    assert active_loan["id"] in full_ids
    assert returned_loan["id"] in full_ids


# --- Case 13: the loan listing is paginated (skip/limit) --------------------
def test_listado_de_prestamos_paginado(client, auth_headers):
    bike_a = _create_bicycle(client, auth_headers, code="L13A")
    bike_b = _create_bicycle(client, auth_headers, code="L13B")
    _create_loan(client, auth_headers, [bike_a["id"]], document="2000016")
    _create_loan(client, auth_headers, [bike_b["id"]], document="2000017")

    first_page = client.get("/loans/?active_only=false&skip=0&limit=1", headers=auth_headers)
    second_page = client.get("/loans/?active_only=false&skip=1&limit=1", headers=auth_headers)

    assert first_page.status_code == 200
    assert len(first_page.json()) == 1
    assert second_page.status_code == 200
    assert len(second_page.json()) == 1
    assert first_page.json()[0]["id"] != second_page.json()[0]["id"]


# --- Case (DEV-004): loans endpoints without a token are rejected ----------
def test_loans_sin_token_es_rechazado(client):
    response = client.get("/loans/")

    assert response.status_code == 401
