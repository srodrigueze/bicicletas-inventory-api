"""Automated regression suite for DEV-001 (Autenticación y gestión de
usuarios). Each test below is the automated version of one of the 15 manual
test cases executed and approved by the user during DEV-001 — see
`Desarrollo/DEV-001 - Autenticacion y gestion de usuarios.md` in the
documentation vault for the original manual run and its evidence.
"""

from app.domain.entities.user import UserRole, UserStatus


# --- Case 1: successful login -----------------------------------------
def test_login_exitoso(client, make_user):
    make_user("Ana Admin", "1000000001", UserRole.ADMINISTRADOR, is_superadmin=True)

    response = client.post("/auth/login", json={"document": "1000000001", "password": "0001"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


# --- Case 2: failed login returns a generic message ---------------------
def test_login_fallido_mensaje_generico(client, make_user):
    make_user("Ana Admin", "1000000002", UserRole.ADMINISTRADOR, is_superadmin=True)

    wrong_password = client.post("/auth/login", json={"document": "1000000002", "password": "9999"})
    wrong_document = client.post("/auth/login", json={"document": "9999999999", "password": "9999"})

    assert wrong_password.status_code == 401
    assert wrong_document.status_code == 401
    assert wrong_password.json()["detail"] == wrong_document.json()["detail"]


# --- Case 3: inactive user cannot log in ---------------------------------
def test_usuario_inactivo_no_puede_loguear(client, make_user):
    make_user(
        "Operador Inactivo",
        "1000000003",
        UserRole.OPERADOR,
        status=UserStatus.INACTIVO,
    )

    response = client.post("/auth/login", json={"document": "1000000003", "password": "0003"})

    assert response.status_code == 401


# --- Case 4: JWT expires after exactly 6 hours ---------------------------
def test_jwt_expira_a_las_6_horas(client, make_user):
    from datetime import datetime, timezone

    import jwt as pyjwt

    from app.core.config import settings

    make_user("Ana Admin", "1000000004", UserRole.ADMINISTRADOR, is_superadmin=True)
    before_login = datetime.now(timezone.utc)
    response = client.post("/auth/login", json={"document": "1000000004", "password": "0004"})
    token = response.json()["access_token"]

    payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    # Allow a small margin for the request/assertion round trip — the token
    # is signed with exp = now + 6h at creation time, not literally "now".
    assert abs((expires_at - before_login).total_seconds() - 6 * 60 * 60) < 5

    expired_token = pyjwt.encode(
        {**payload, "exp": payload["exp"] - 6 * 60 * 60 - 1},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    protected = client.get("/users/", headers={"Authorization": f"Bearer {expired_token}"})
    assert protected.status_code == 401


# --- Case 5: a regular admin cannot manage another admin -----------------
def test_admin_normal_no_puede_gestionar_a_otro_admin(client, make_user, token_for):
    make_user("Superadmin", "1000000005", UserRole.ADMINISTRADOR, is_superadmin=True)
    admin_a = make_user("Admin A", "1000000006", UserRole.ADMINISTRADOR)
    admin_b = make_user("Admin B", "1000000007", UserRole.ADMINISTRADOR)
    headers = token_for("1000000006", "0006")

    edit = client.patch(f"/users/{admin_b.id}", json={"full_name": "Nuevo nombre"}, headers=headers)
    deactivate = client.patch(f"/users/{admin_b.id}", json={"status": "inactivo"}, headers=headers)

    assert edit.status_code == 403
    assert deactivate.status_code == 403


# --- Case 6: a regular admin CAN manage operators -------------------------
def test_admin_normal_gestiona_operadores(client, make_user, token_for):
    make_user("Admin", "1000000008", UserRole.ADMINISTRADOR)
    operador = make_user("Operador", "1000000009", UserRole.OPERADOR)
    headers = token_for("1000000008", "0008")

    create = client.post(
        "/users/",
        json={"full_name": "Nuevo Operador", "document": "1000000010", "role": "operador"},
        headers=headers,
    )
    edit = client.patch(f"/users/{operador.id}", json={"full_name": "Operador Editado"}, headers=headers)
    deactivate = client.patch(f"/users/{operador.id}", json={"status": "inactivo"}, headers=headers)

    assert create.status_code == 201
    assert edit.status_code == 200
    assert deactivate.status_code == 200
    assert deactivate.json()["status"] == "inactivo"


# --- Case 7: the superadmin can manage anyone except themself -------------
def test_superadmin_gestiona_a_cualquiera(client, make_user, token_for):
    superadmin = make_user("Superadmin", "1000000011", UserRole.ADMINISTRADOR, is_superadmin=True)
    other_admin = make_user("Admin", "1000000012", UserRole.ADMINISTRADOR)
    headers = token_for("1000000011", "0011")

    edit_admin = client.patch(f"/users/{other_admin.id}", json={"full_name": "Editado"}, headers=headers)
    deactivate_admin = client.patch(f"/users/{other_admin.id}", json={"status": "inactivo"}, headers=headers)

    assert edit_admin.status_code == 200
    assert deactivate_admin.status_code == 200


# --- Case 8: nobody can deactivate/edit themself, not even the superadmin -
def test_nadie_puede_autodesactivarse(client, make_user, token_for):
    superadmin = make_user("Superadmin", "1000000013", UserRole.ADMINISTRADOR, is_superadmin=True)
    admin = make_user("Admin", "1000000014", UserRole.ADMINISTRADOR)

    superadmin_headers = token_for("1000000013", "0013")
    admin_headers = token_for("1000000014", "0014")

    superadmin_self_edit = client.patch(
        f"/users/{superadmin.id}", json={"status": "inactivo"}, headers=superadmin_headers
    )
    admin_self_edit = client.patch(f"/users/{admin.id}", json={"status": "inactivo"}, headers=admin_headers)

    assert superadmin_self_edit.status_code == 403
    assert admin_self_edit.status_code == 403


# --- Case 9: administrators' document is masked in list and detail -------
def test_documento_de_admin_enmascarado(client, make_user, token_for):
    superadmin = make_user("Superadmin", "1000000015", UserRole.ADMINISTRADOR, is_superadmin=True)
    headers = token_for("1000000015", "0015")

    listing = client.get("/users/", headers=headers)
    detail = client.get(f"/users/{superadmin.id}", headers=headers)

    assert listing.status_code == 200
    assert all(u["document"] == "****" for u in listing.json() if u["role"] == "administrador")
    assert detail.status_code == 200
    assert detail.json()["document"] == "****"


# --- Case: GET /users/me returns the caller's own data ---------------------
def test_get_mi_usuario_devuelve_datos_propios(client, make_user, token_for):
    operador = make_user("Operador", "1000000031", UserRole.OPERADOR)
    headers = token_for("1000000031", "0031")

    response = client.get("/users/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == operador.id
    assert body["document"] == "1000000031"
    assert body["role"] == "operador"


# --- Case: GET /users/me masks the document for an administrator ----------
def test_get_mi_usuario_enmascara_documento_si_es_admin(client, make_user, token_for):
    make_user("Admin", "1000000032", UserRole.ADMINISTRADOR, is_superadmin=True)
    headers = token_for("1000000032", "0032")

    response = client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["document"] == "****"


# --- Case: GET /users/me without a token is rejected ------------------------
def test_get_mi_usuario_sin_token_es_rechazado(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_listado_de_usuarios_paginado(client, make_user, token_for):
    make_user("Superadmin", "1000000016", UserRole.ADMINISTRADOR, is_superadmin=True)
    make_user("Operador 1", "1000000017", UserRole.OPERADOR)
    make_user("Operador 2", "1000000018", UserRole.OPERADOR)
    headers = token_for("1000000016", "0016")

    response = client.get("/users/?skip=0&limit=1", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


# --- Case 10: password change requires the correct current password ------
def test_cambio_contrasena_exige_contrasena_actual_correcta(client, make_user, token_for):
    make_user("Operador", "1000000019", UserRole.OPERADOR)
    headers = token_for("1000000019", "0019")

    wrong_current = client.post(
        "/users/me/change-password",
        json={"current_password": "0000", "new_password": "nueva123"},
        headers=headers,
    )

    assert wrong_current.status_code == 400


# --- Case 11: password change requires a minimum of 6 characters ---------
def test_cambio_contrasena_exige_minimo_6_caracteres(client, make_user, token_for):
    make_user("Operador", "1000000020", UserRole.OPERADOR)
    headers = token_for("1000000020", "0020")

    too_short = client.post(
        "/users/me/change-password",
        json={"current_password": "0020", "new_password": "abc"},
        headers=headers,
    )

    assert too_short.status_code == 422


def test_cambio_contrasena_exitoso_desliga_de_la_derivada(client, make_user, token_for):
    make_user("Operador", "1000000021", UserRole.OPERADOR)
    headers = token_for("1000000021", "0021")

    changed = client.post(
        "/users/me/change-password",
        json={"current_password": "0021", "new_password": "nuevaClave123"},
        headers=headers,
    )
    old_password_login = client.post("/auth/login", json={"document": "1000000021", "password": "0021"})
    new_password_login = client.post(
        "/auth/login", json={"document": "1000000021", "password": "nuevaClave123"}
    )

    assert changed.status_code == 200
    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200


# --- Case 12: admin -> operator password reset ----------------------------
def test_reset_password_admin_a_operador(client, make_user, token_for):
    make_user("Admin", "1000000022", UserRole.ADMINISTRADOR)
    operador = make_user("Operador", "1000000023", UserRole.OPERADOR)
    admin_headers = token_for("1000000022", "0022")

    client.post(
        "/users/me/change-password",
        json={"current_password": "0023", "new_password": "otraClave123"},
        headers=token_for("1000000023", "0023"),
    )

    reset = client.post(f"/users/{operador.id}/reset-password", headers=admin_headers)
    login_with_derived = client.post("/auth/login", json={"document": "1000000023", "password": "0023"})

    assert reset.status_code == 200
    assert login_with_derived.status_code == 200


# --- Case 13: superadmin -> admin password reset ---------------------------
def test_reset_password_superadmin_a_admin(client, make_user, token_for):
    make_user("Superadmin", "1000000024", UserRole.ADMINISTRADOR, is_superadmin=True)
    admin = make_user("Admin", "1000000025", UserRole.ADMINISTRADOR)
    superadmin_headers = token_for("1000000024", "0024")

    client.post(
        "/users/me/change-password",
        json={"current_password": "0025", "new_password": "otraClave123"},
        headers=token_for("1000000025", "0025"),
    )

    reset = client.post(f"/users/{admin.id}/reset-password", headers=superadmin_headers)
    login_with_derived = client.post("/auth/login", json={"document": "1000000025", "password": "0025"})

    assert reset.status_code == 200
    assert login_with_derived.status_code == 200


# --- Case 14: an operator cannot reset anyone's password ------------------
def test_operador_no_puede_resetear_a_nadie(client, make_user, token_for):
    operador = make_user("Operador", "1000000026", UserRole.OPERADOR)
    otro_operador = make_user("Otro Operador", "1000000027", UserRole.OPERADOR)
    headers = token_for("1000000026", "0026")

    reset = client.post(f"/users/{otro_operador.id}/reset-password", headers=headers)

    assert reset.status_code == 403


def test_admin_normal_no_puede_resetear_a_otro_admin(client, make_user, token_for):
    make_user("Admin A", "1000000028", UserRole.ADMINISTRADOR)
    admin_b = make_user("Admin B", "1000000029", UserRole.ADMINISTRADOR)
    headers = token_for("1000000028", "0028")

    reset = client.post(f"/users/{admin_b.id}/reset-password", headers=headers)

    assert reset.status_code == 403


# --- Case 15: a document with letters is rejected --------------------------
def test_documento_con_letras_es_rechazado(client, make_user, token_for):
    make_user("Admin", "1000000030", UserRole.ADMINISTRADOR)
    headers = token_for("1000000030", "0030")

    response = client.post(
        "/users/",
        json={"full_name": "Invalido", "document": "abc123", "role": "operador"},
        headers=headers,
    )

    assert response.status_code == 422
