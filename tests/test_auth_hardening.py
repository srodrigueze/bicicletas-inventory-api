"""Regression suite for the login hardening: forced change of the guessable
initial password, and temporary lockout after repeated failed logins.
"""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from app.core.config import settings
from app.domain.entities.user import UserRole
from app.infrastructure.repositories.user_repository_sql import SqlUserRepository


def _login(client, document: str, password: str):
    return client.post("/auth/login", json={"document": document, "password": password})


def _fail_logins(client, document: str, times: int) -> None:
    for _ in range(times):
        assert _login(client, document, "wrong-password").status_code == 401


# --- Forced password change ---------------------------------------------
def test_usuario_creado_por_api_debe_cambiar_contrasena(client, make_user, token_for):
    make_user("Admin", "2000000001", UserRole.ADMINISTRADOR)
    admin_headers = token_for("2000000001", "0001")
    created = client.post(
        "/users/",
        json={"full_name": "Nuevo Operador", "document": "2000000002", "role": "operador"},
        headers=admin_headers,
    )

    login = _login(client, "2000000002", "0002")

    assert created.status_code == 201
    assert created.json()["must_change_password"] is True
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True


def test_con_cambio_pendiente_solo_se_puede_cambiar_la_contrasena(client, make_user, token_for):
    make_user("Operador", "2000000003", UserRole.OPERADOR, must_change_password=True)
    headers = token_for("2000000003", "0003")

    blocked = client.get("/bicycles/", headers=headers)
    me = client.get("/users/me", headers=headers)

    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Password change required"
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True


def test_con_cambio_pendiente_un_admin_tampoco_accede_a_rutas_de_admin(client, make_user, token_for):
    make_user("Admin", "2000000004", UserRole.ADMINISTRADOR, must_change_password=True)
    headers = token_for("2000000004", "0004")

    response = client.get("/users/", headers=headers)

    assert response.status_code == 403


def test_cambiar_la_contrasena_libera_la_cuenta(client, make_user, token_for):
    make_user("Operador", "2000000005", UserRole.OPERADOR, must_change_password=True)
    headers = token_for("2000000005", "0005")

    changed = client.post(
        "/users/me/change-password",
        json={"current_password": "0005", "new_password": "nuevaClave123"},
        headers=headers,
    )
    new_login = _login(client, "2000000005", "nuevaClave123")
    new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}

    assert changed.status_code == 200
    assert new_login.json()["must_change_password"] is False
    assert client.get("/bicycles/", headers=new_headers).status_code == 200


def test_reset_password_vuelve_a_exigir_el_cambio(client, make_user, token_for):
    make_user("Admin", "2000000006", UserRole.ADMINISTRADOR)
    operador = make_user("Operador", "2000000007", UserRole.OPERADOR)
    admin_headers = token_for("2000000006", "0006")

    reset = client.post(f"/users/{operador.id}/reset-password", headers=admin_headers)
    login = _login(client, "2000000007", "0007")

    assert reset.status_code == 200
    assert login.json()["must_change_password"] is True


# --- Login lockout ----------------------------------------------------------
def test_bloqueo_tras_demasiados_intentos_fallidos(client, make_user):
    make_user("Operador", "2000000008", UserRole.OPERADOR)
    _fail_logins(client, "2000000008", settings.login_max_attempts)

    # Even the correct password is refused while the account is locked.
    locked = _login(client, "2000000008", "0008")

    assert locked.status_code == 429
    assert 0 < int(locked.headers["Retry-After"]) <= settings.login_lock_minutes * 60


def test_ultimo_intento_permitido_con_clave_correcta_entra_y_reinicia_el_contador(client, make_user):
    make_user("Operador", "2000000009", UserRole.OPERADOR)
    _fail_logins(client, "2000000009", settings.login_max_attempts - 1)

    assert _login(client, "2000000009", "0009").status_code == 200

    # The counter restarted: another full round of failures is tolerated.
    _fail_logins(client, "2000000009", settings.login_max_attempts - 1)
    assert _login(client, "2000000009", "0009").status_code == 200


def test_el_bloqueo_expira(client, make_user, db_session):
    user = make_user("Operador", "2000000010", UserRole.OPERADOR)
    _fail_logins(client, "2000000010", settings.login_max_attempts)
    assert _login(client, "2000000010", "0010").status_code == 429

    user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    SqlUserRepository(db_session).update(user)

    assert _login(client, "2000000010", "0010").status_code == 200


def test_reset_password_desbloquea_la_cuenta(client, make_user, token_for):
    make_user("Admin", "2000000011", UserRole.ADMINISTRADOR)
    operador = make_user("Operador", "2000000012", UserRole.OPERADOR)
    admin_headers = token_for("2000000011", "0011")
    _fail_logins(client, "2000000012", settings.login_max_attempts)
    assert _login(client, "2000000012", "0012").status_code == 429

    client.post(f"/users/{operador.id}/reset-password", headers=admin_headers)

    assert _login(client, "2000000012", "0012").status_code == 200


def test_el_bloqueo_es_por_cuenta(client, make_user):
    make_user("Operador A", "2000000013", UserRole.OPERADOR)
    make_user("Operador B", "2000000014", UserRole.OPERADOR)
    _fail_logins(client, "2000000013", settings.login_max_attempts)

    assert _login(client, "2000000014", "0014").status_code == 200


# --- Token revocation --------------------------------------------------------
def test_cambiar_la_contrasena_revoca_los_tokens_anteriores(client, make_user, token_for):
    make_user("Operador", "2000000015", UserRole.OPERADOR)
    old_headers = token_for("2000000015", "0015")
    assert client.get("/users/me", headers=old_headers).status_code == 200

    client.post(
        "/users/me/change-password",
        json={"current_password": "0015", "new_password": "nuevaClave123"},
        headers=old_headers,
    )

    assert client.get("/users/me", headers=old_headers).status_code == 401
    assert _login(client, "2000000015", "nuevaClave123").status_code == 200


def test_reset_password_revoca_los_tokens_del_usuario_reseteado(client, make_user, token_for):
    make_user("Admin", "2000000016", UserRole.ADMINISTRADOR)
    operador = make_user("Operador", "2000000017", UserRole.OPERADOR)
    operador_headers = token_for("2000000017", "0017")
    admin_headers = token_for("2000000016", "0016")

    client.post(f"/users/{operador.id}/reset-password", headers=admin_headers)

    assert client.get("/users/me", headers=operador_headers).status_code == 401
    # The admin who did the reset keeps their own session.
    assert client.get("/users/me", headers=admin_headers).status_code == 200


def test_token_sin_claim_de_version_se_trata_como_version_0(client, make_user):
    user = make_user("Operador", "2000000018", UserRole.OPERADOR)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    legacy = pyjwt.encode(
        {"sub": str(user.id), "exp": expires}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    stale = pyjwt.encode(
        {"sub": str(user.id), "ver": 5, "exp": expires}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    assert client.get("/users/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 200
    assert client.get("/users/me", headers={"Authorization": f"Bearer {stale}"}).status_code == 401


# --- Password audit trail -----------------------------------------------------
def test_cambio_y_reset_de_contrasena_quedan_en_la_auditoria(client, make_user, token_for):
    admin = make_user("Admin", "2000000020", UserRole.ADMINISTRADOR)
    operador = make_user("Operador", "2000000021", UserRole.OPERADOR)
    admin_headers = token_for("2000000020", "0020")
    client.post(
        "/users/me/change-password",
        json={"current_password": "0021", "new_password": "nuevaClave123"},
        headers=token_for("2000000021", "0021"),
    )
    client.post(f"/users/{operador.id}/reset-password", headers=admin_headers)

    logs = client.get("/audits/?entity_name=User", headers=admin_headers).json()

    recorded = {(log["action"], log["user_id"], log["entity_id"]) for log in logs}
    assert ("password_change", operador.id, operador.id) in recorded
    assert ("password_reset", admin.id, operador.id) in recorded
    # The audit trail never carries any password material.
    assert all("password" not in (log["new_values"] or "") for log in logs)


# --- bcrypt 72-byte limit ---------------------------------------------------------
def test_contrasena_nueva_de_mas_de_72_bytes_es_rechazada(client, make_user, token_for):
    make_user("Operador", "2000000022", UserRole.OPERADOR)
    headers = token_for("2000000022", "0022")

    response = client.post(
        "/users/me/change-password",
        json={"current_password": "0022", "new_password": "a" * 73},
        headers=headers,
    )

    assert response.status_code == 422


def test_login_con_contrasena_de_mas_de_72_bytes_da_401_y_no_500(client, make_user):
    make_user("Operador", "2000000023", UserRole.OPERADOR)

    response = _login(client, "2000000023", "a" * 200)

    assert response.status_code == 401


# --- Login timing ---------------------------------------------------------------
def test_login_de_documento_inexistente_o_inactivo_tambien_gasta_la_verificacion(client, make_user, monkeypatch):
    from app.domain.entities.user import UserStatus

    make_user("Inactivo", "2000000024", UserRole.OPERADOR, status=UserStatus.INACTIVO)
    calls = []
    monkeypatch.setattr("app.services.user_service.burn_password_check", lambda password: calls.append(password))

    _login(client, "9999999998", "cualquiera")
    _login(client, "2000000024", "0024")

    assert len(calls) == 2
