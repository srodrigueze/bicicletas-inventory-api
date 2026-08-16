"""Automated regression suite for DEV-002 (Inventario de bicicletas). Each
test below is the automated version of one of the 10 test cases approved by
the user during DEV-002 — see
`Desarrollo/DEV-002 - Inventario de bicicletas.md` in the documentation
vault for the criteria/test-case definition and the validation report.
"""


def _create_bicycle(client, **overrides):
    payload = {
        "code": "B0001",
        "condition": "good",
        "size": "medium",
        "rueditas_asistencia": False,
        "tiene_pedales": True,
        "observations": None,
    }
    payload.update(overrides)
    response = client.post("/bicycles/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- Case 1: creating a bicycle with a duplicate code is rejected ---------
def test_creacion_con_codigo_duplicado_es_rechazada(client):
    _create_bicycle(client, code="B1")

    duplicate = client.post(
        "/bicycles/",
        json={
            "code": "B1",
            "condition": "good",
            "size": "small",
            "rueditas_asistencia": True,
            "tiene_pedales": False,
        },
    )

    assert duplicate.status_code == 409


# --- Case 2: editing every field, including the code, works ---------------
def test_edicion_de_todos_los_campos_incluido_codigo(client):
    bicycle = _create_bicycle(client, code="B2")

    response = client.patch(
        f"/bicycles/{bicycle['id']}",
        json={
            "code": "B2X",
            "condition": "bad",
            "size": "large",
            "rueditas_asistencia": True,
            "tiene_pedales": False,
            "observations": "Freno trasero flojo",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == bicycle["id"]
    assert body["code"] == "B2X"
    assert body["condition"] == "bad"
    assert body["size"] == "large"
    assert body["rueditas_asistencia"] is True
    assert body["tiene_pedales"] is False
    assert body["observations"] == "Freno trasero flojo"


# --- Case 3: availability does not depend on physical condition -----------
def test_disponibilidad_no_depende_de_condicion_fisica(client):
    good_bike = _create_bicycle(client, code="B3G", condition="good")
    bad_bike = _create_bicycle(client, code="B3B", condition="bad")

    good_read = client.get(f"/bicycles/{good_bike['id']}").json()
    bad_read = client.get(f"/bicycles/{bad_bike['id']}").json()

    assert good_read["is_available"] is True
    assert bad_read["is_available"] is True


# --- Case 4: a bicycle needing repairs can still be loaned (is available) -
def test_bicicleta_necesita_reparaciones_puede_prestarse(client):
    bicycle = _create_bicycle(client, code="B4", condition="bad")

    response = client.get(f"/bicycles/{bicycle['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["condition"] == "bad"
    assert body["en_posesion_jac"] is True
    assert body["is_available"] is True


# --- Case 5: logical delete does not remove the row ------------------------
def test_baja_logica_no_borra_la_fila(client):
    bicycle = _create_bicycle(client, code="B5")

    delete = client.delete(f"/bicycles/{bicycle['id']}")
    still_exists = client.get(f"/bicycles/{bicycle['id']}")

    assert delete.status_code == 200, delete.text
    assert delete.json()["en_posesion_jac"] is False
    assert still_exists.status_code == 200
    assert still_exists.json()["en_posesion_jac"] is False


# --- Case 6: a deleted bicycle cannot be loaned (is not available) --------
def test_bicicleta_dada_de_baja_no_puede_ser_prestada(client):
    bicycle = _create_bicycle(client, code="B6")

    client.delete(f"/bicycles/{bicycle['id']}")
    response = client.get(f"/bicycles/{bicycle['id']}")

    assert response.status_code == 200
    assert response.json()["is_available"] is False


# --- Case 7: the logical delete is reversible via restore -----------------
def test_baja_es_reversible_via_restore(client):
    bicycle = _create_bicycle(client, code="B7")
    client.delete(f"/bicycles/{bicycle['id']}")

    restore = client.patch(f"/bicycles/{bicycle['id']}/restore")

    assert restore.status_code == 200, restore.text
    body = restore.json()
    assert body["en_posesion_jac"] is True
    assert body["is_available"] is True


# --- Case 8: filtering by size, condition, rueditas, pedales, possession --
def test_filtros_de_listado(client):
    _create_bicycle(
        client, code="F1", size="small", condition="good", rueditas_asistencia=True, tiene_pedales=True
    )
    _create_bicycle(
        client, code="F2", size="large", condition="bad", rueditas_asistencia=False, tiene_pedales=False
    )
    deleted = _create_bicycle(
        client, code="F3", size="medium", condition="good", rueditas_asistencia=False, tiene_pedales=True
    )
    client.delete(f"/bicycles/{deleted['id']}")

    by_size = client.get("/bicycles/?size=small")
    by_condition = client.get("/bicycles/?condition=bad")
    by_rueditas = client.get("/bicycles/?rueditas_asistencia=true")
    by_pedales = client.get("/bicycles/?tiene_pedales=false")
    by_posesion = client.get("/bicycles/?en_posesion_jac=false")

    assert [b["code"] for b in by_size.json()] == ["F1"]
    assert [b["code"] for b in by_condition.json()] == ["F2"]
    assert [b["code"] for b in by_rueditas.json()] == ["F1"]
    assert [b["code"] for b in by_pedales.json()] == ["F2"]
    assert [b["code"] for b in by_posesion.json()] == ["F3"]


# --- Case 9: the listing is paginated (skip/limit) -------------------------
def test_listado_paginado(client):
    _create_bicycle(client, code="P1")
    _create_bicycle(client, code="P2")
    _create_bicycle(client, code="P3")

    first_page = client.get("/bicycles/?skip=0&limit=1")
    second_page = client.get("/bicycles/?skip=1&limit=1")

    assert first_page.status_code == 200
    assert len(first_page.json()) == 1
    assert second_page.status_code == 200
    assert len(second_page.json()) == 1
    assert first_page.json()[0]["code"] != second_page.json()[0]["code"]


# --- Case 10: rueditas_asistencia/tiene_pedales persist on create/update --
def test_rueditas_y_pedales_se_guardan_y_leen_correctamente(client):
    bicycle = _create_bicycle(client, code="B10", rueditas_asistencia=True, tiene_pedales=False)

    assert bicycle["rueditas_asistencia"] is True
    assert bicycle["tiene_pedales"] is False

    updated = client.patch(
        f"/bicycles/{bicycle['id']}",
        json={"rueditas_asistencia": False, "tiene_pedales": True},
    )

    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["rueditas_asistencia"] is False
    assert body["tiene_pedales"] is True
