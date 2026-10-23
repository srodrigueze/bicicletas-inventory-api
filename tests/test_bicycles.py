"""Automated regression suite for DEV-002 (Inventario de bicicletas). Each
test below is the automated version of one of the 10 test cases approved by
the user during DEV-002 — see
`Desarrollo/DEV-002 - Inventario de bicicletas.md` in the documentation
vault for the criteria/test-case definition and the validation report.

Since DEV-004 added JWT protection to the bicycles endpoints, every request
here goes through `auth_headers` (an authenticated operador).
"""


# Minimal byte strings carrying each format's real signature. Uploads are
# validated by content, so a made-up payload is no longer accepted.
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 16
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 16
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 8


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


# --- Case 1: creating a bicycle with a duplicate code is rejected ---------
def test_creacion_con_codigo_duplicado_es_rechazada(client, auth_headers):
    _create_bicycle(client, auth_headers, code="B1")

    duplicate = client.post(
        "/bicycles/",
        json={
            "code": "B1",
            "condition": "good",
            "size": "small",
            "rueditas_asistencia": True,
            "tiene_pedales": False,
        },
        headers=auth_headers,
    )

    assert duplicate.status_code == 409


# --- Case 2: editing every field, including the code, works ---------------
def test_edicion_de_todos_los_campos_incluido_codigo(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="B2")

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
        headers=auth_headers,
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
def test_disponibilidad_no_depende_de_condicion_fisica(client, auth_headers):
    good_bike = _create_bicycle(client, auth_headers, code="B3G", condition="good")
    bad_bike = _create_bicycle(client, auth_headers, code="B3B", condition="bad")

    good_read = client.get(f"/bicycles/{good_bike['id']}", headers=auth_headers).json()
    bad_read = client.get(f"/bicycles/{bad_bike['id']}", headers=auth_headers).json()

    assert good_read["is_available"] is True
    assert bad_read["is_available"] is True


# --- Case 4: a bicycle needing repairs can still be loaned (is available) -
def test_bicicleta_necesita_reparaciones_puede_prestarse(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="B4", condition="bad")

    response = client.get(f"/bicycles/{bicycle['id']}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["condition"] == "bad"
    assert body["en_posesion_jac"] is True
    assert body["is_available"] is True


# --- Case 5: logical delete does not remove the row ------------------------
def test_baja_logica_no_borra_la_fila(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="B5")

    delete = client.delete(f"/bicycles/{bicycle['id']}", headers=auth_headers)
    still_exists = client.get(f"/bicycles/{bicycle['id']}", headers=auth_headers)

    assert delete.status_code == 200, delete.text
    assert delete.json()["en_posesion_jac"] is False
    assert still_exists.status_code == 200
    assert still_exists.json()["en_posesion_jac"] is False


# --- Case 6: a deleted bicycle cannot be loaned (is not available) --------
def test_bicicleta_dada_de_baja_no_puede_ser_prestada(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="B6")

    client.delete(f"/bicycles/{bicycle['id']}", headers=auth_headers)
    response = client.get(f"/bicycles/{bicycle['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["is_available"] is False


# --- Case 7: the logical delete is reversible via restore -----------------
def test_baja_es_reversible_via_restore(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="B7")
    client.delete(f"/bicycles/{bicycle['id']}", headers=auth_headers)

    restore = client.patch(f"/bicycles/{bicycle['id']}/restore", headers=auth_headers)

    assert restore.status_code == 200, restore.text
    body = restore.json()
    assert body["en_posesion_jac"] is True
    assert body["is_available"] is True


# --- Case 8: filtering by size, condition, rueditas, pedales, possession --
def test_filtros_de_listado(client, auth_headers):
    _create_bicycle(
        client, auth_headers, code="F1", size="small", condition="good", rueditas_asistencia=True, tiene_pedales=True
    )
    _create_bicycle(
        client, auth_headers, code="F2", size="large", condition="bad", rueditas_asistencia=False, tiene_pedales=False
    )
    deleted = _create_bicycle(
        client, auth_headers, code="F3", size="medium", condition="good", rueditas_asistencia=False, tiene_pedales=True
    )
    client.delete(f"/bicycles/{deleted['id']}", headers=auth_headers)

    by_size = client.get("/bicycles/?size=small", headers=auth_headers)
    by_condition = client.get("/bicycles/?condition=bad", headers=auth_headers)
    by_rueditas = client.get("/bicycles/?rueditas_asistencia=true", headers=auth_headers)
    by_pedales = client.get("/bicycles/?tiene_pedales=false", headers=auth_headers)
    by_posesion = client.get("/bicycles/?en_posesion_jac=false", headers=auth_headers)

    assert [b["code"] for b in by_size.json()] == ["F1"]
    assert [b["code"] for b in by_condition.json()] == ["F2"]
    assert [b["code"] for b in by_rueditas.json()] == ["F1"]
    assert [b["code"] for b in by_pedales.json()] == ["F2"]
    assert [b["code"] for b in by_posesion.json()] == ["F3"]


# --- Case 9: the listing is paginated (skip/limit) -------------------------
def test_listado_paginado(client, auth_headers):
    _create_bicycle(client, auth_headers, code="P1")
    _create_bicycle(client, auth_headers, code="P2")
    _create_bicycle(client, auth_headers, code="P3")

    first_page = client.get("/bicycles/?skip=0&limit=1", headers=auth_headers)
    second_page = client.get("/bicycles/?skip=1&limit=1", headers=auth_headers)

    assert first_page.status_code == 200
    assert len(first_page.json()) == 1
    assert second_page.status_code == 200
    assert len(second_page.json()) == 1
    assert first_page.json()[0]["code"] != second_page.json()[0]["code"]


# --- Case 10: rueditas_asistencia/tiene_pedales persist on create/update --
def test_rueditas_y_pedales_se_guardan_y_leen_correctamente(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="B10", rueditas_asistencia=True, tiene_pedales=False)

    assert bicycle["rueditas_asistencia"] is True
    assert bicycle["tiene_pedales"] is False

    updated = client.patch(
        f"/bicycles/{bicycle['id']}",
        json={"rueditas_asistencia": False, "tiene_pedales": True},
        headers=auth_headers,
    )

    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["rueditas_asistencia"] is False
    assert body["tiene_pedales"] is True


# --- Case (DEV-004): bicycles endpoints without a token are rejected -------
def test_bicycles_sin_token_es_rechazado(client):
    response = client.get("/bicycles/")

    assert response.status_code == 401


# --- Case (DEV-006): image_path is persisted and returned ------------------
def test_crear_bicicleta_con_image_path_se_persiste(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="I1", image_path="bicicletas/i1.jpg")

    assert bicycle["image_path"] == "bicicletas/i1.jpg"


# --- Case (DEV-006): without image_path, both fields are null --------------
def test_crear_bicicleta_sin_image_path_expone_nulos(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="I2")

    assert bicycle["image_path"] is None
    assert bicycle["image_url"] is None


# --- Case (DEV-006): image_url concatenates the configured base URL --------
def test_image_url_concatena_ruta_base_configurada(client, auth_headers):
    from app.core.config import settings

    bicycle = _create_bicycle(client, auth_headers, code="I3", image_path="bicicletas/i3.jpg")

    assert bicycle["image_url"] == f"{settings.image_base_url}bicicletas/i3.jpg"


# --- Case (DEV-006): editing image_path updates the value ------------------
def test_editar_image_path_actualiza_el_valor(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="I4")

    response = client.patch(
        f"/bicycles/{bicycle['id']}",
        json={"image_path": "bicicletas/i4-nueva.jpg"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["image_path"] == "bicicletas/i4-nueva.jpg"


# --- Case (DEV-007): uploading a valid image stores it in GCS and updates image_path
def test_subir_imagen_valida_actualiza_image_path(client, auth_headers):
    from google.cloud import storage

    from app.core.config import settings

    bicycle = _create_bicycle(client, auth_headers, code="U1")

    response = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("foto.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["image_path"].startswith(f"bicicletas/{bicycle['id']}/")
    assert body["image_path"].endswith(".jpg")
    assert body["image_url"] == f"{settings.image_base_url}{body['image_path']}"

    gcs_client = storage.Client()
    blob = gcs_client.bucket(settings.gcs_bucket_name).blob(body["image_path"])
    assert blob.exists()


# --- Case (DEV-007): an unsupported content type is rejected ---------------
def test_subir_imagen_con_tipo_no_soportado_es_rechazada(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="U2")

    response = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("archivo.txt", b"no es una imagen", "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 415


# --- Upload hardening: the real content decides, not the client's claims -----
def test_subir_imagen_con_contenido_falso_es_rechazada(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="U6")

    response = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("foto.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 415


def test_subir_imagen_png_y_webp_validas(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="U7")

    png = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("a.png", PNG_BYTES, "image/png")},
        headers=auth_headers,
    )
    webp = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("a.webp", WEBP_BYTES, "image/webp")},
        headers=auth_headers,
    )

    assert png.status_code == 200, png.text
    assert png.json()["image_path"].endswith(".png")
    assert webp.status_code == 200, webp.text
    assert webp.json()["image_path"].endswith(".webp")


def test_subir_imagen_ignora_la_extension_enviada_por_el_cliente(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="U8")

    response = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("malicioso.html", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["image_path"].endswith(".jpg")


# --- Case (DEV-007): a file over 5MB is rejected ----------------------------
def test_subir_imagen_muy_grande_es_rechazada(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="U3")
    oversized_content = b"0" * (5 * 1024 * 1024 + 1)

    response = client.post(
        f"/bicycles/{bicycle['id']}/image",
        files={"file": ("grande.jpg", oversized_content, "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 413


# --- Case (DEV-007): uploading for a nonexistent bicycle returns 404 -------
def test_subir_imagen_a_bicicleta_inexistente_da_404(client, auth_headers):
    response = client.post(
        "/bicycles/999999/image",
        files={"file": ("foto.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 404


# --- Case (DEV-007): the upload endpoint requires authentication -----------
def test_subir_imagen_sin_token_es_rechazado(client):
    response = client.post(
        "/bicycles/1/image",
        files={"file": ("foto.jpg", b"contenido", "image/jpeg")},
    )

    assert response.status_code == 401


# --- Case (DEV-008): numero_frenos defaults to 2 when not sent -------------
def test_crear_bicicleta_sin_numero_frenos_usa_el_valor_por_defecto(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="FR1")

    assert bicycle["numero_frenos"] == 2


# --- Case (DEV-008): numero_frenos 0 and 1 are accepted ---------------------
def test_crear_bicicleta_con_numero_frenos_valido_se_persiste(client, auth_headers):
    sin_frenos = _create_bicycle(client, auth_headers, code="FR2", numero_frenos=0)
    un_freno = _create_bicycle(client, auth_headers, code="FR3", numero_frenos=1)

    assert sin_frenos["numero_frenos"] == 0
    assert un_freno["numero_frenos"] == 1


# --- Case (DEV-008): a value outside 0-2 is rejected ------------------------
def test_crear_bicicleta_con_numero_frenos_invalido_es_rechazado(client, auth_headers):
    response = client.post(
        "/bicycles/",
        json={
            "code": "FR4",
            "condition": "good",
            "size": "medium",
            "rueditas_asistencia": False,
            "tiene_pedales": True,
            "numero_frenos": 3,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


# --- Case (DEV-008): editing numero_frenos updates the value ---------------
def test_editar_numero_frenos_actualiza_el_valor(client, auth_headers):
    bicycle = _create_bicycle(client, auth_headers, code="FR5")

    response = client.patch(f"/bicycles/{bicycle['id']}", json={"numero_frenos": 1}, headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["numero_frenos"] == 1


# --- Code filter: wildcards typed by the user are literal text -------------
def test_filtro_por_codigo_trata_los_comodines_como_texto_literal(client, auth_headers):
    _create_bicycle(client, auth_headers, code="CMD1")
    _create_bicycle(client, auth_headers, code="CMD2")

    percent = client.get("/bicycles/?code=%25", headers=auth_headers)
    underscore = client.get("/bicycles/?code=_", headers=auth_headers)
    partial = client.get("/bicycles/?code=cmd", headers=auth_headers)

    assert percent.json() == []
    assert underscore.json() == []
    # Plain partial, case-insensitive matching keeps working.
    assert len(partial.json()) == 2
