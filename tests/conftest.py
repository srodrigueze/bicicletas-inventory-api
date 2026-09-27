"""Test suite configuration.

Runs against the dedicated Neon branch "test" (never against dev or
production), whose connection strings live in `.env.test` at the repo root.
That file is loaded and injected into the process environment *before* any
`app.*` module is imported, so `app.core.config.Settings` (which reads
`DATABASE_URL`/`DATABASE_URL_DIRECT` from the environment) picks up the test
database transparently, with zero changes to application code.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

REPO_ROOT = Path(__file__).resolve().parent.parent

_test_env = dotenv_values(REPO_ROOT / ".env.test")
if not _test_env.get("DATABASE_URL"):
    raise RuntimeError(
        "tests/conftest.py: .env.test is missing or has no DATABASE_URL. "
        "Create it at the repo root pointing to the Neon 'test' branch."
    )
os.environ.update({k: v for k, v in _test_env.items() if v is not None})

# Import entity modules (not app.main yet) so SQLModel.metadata is fully
# populated for the truncate-all-tables cleanup below, regardless of which
# test file runs first.
from app.domain.entities import audit_log, bicycle, client, loan, user  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_database():
    """Applies Alembic migrations to the test branch once per test run."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        cwd=str(REPO_ROOT),
    )
    yield


@pytest.fixture(autouse=True)
def _clean_gcs_test_bucket():
    """Deletes every object uploaded during the test from the real GCS test
    bucket, mirroring the DB truncate-after-each-test cleanup below — tests
    upload for real (no mocks), same philosophy as the Neon test branch."""
    yield
    from google.cloud import storage

    from app.core.config import settings

    client = storage.Client()
    bucket = client.bucket(settings.gcs_bucket_name)
    for blob in client.list_blobs(bucket, prefix="bicicletas/"):
        blob.delete()


@pytest.fixture(autouse=True)
def _clean_database(_migrated_test_database):
    """Truncates every app table after each test so tests don't leak state
    into one another — cheaper and simpler than a transactional rollback
    given the app opens its own session per request via `get_session`."""
    yield
    from app.core.database import engine

    table_names = ", ".join(f'"{table.name}"' for table in SQLModel.metadata.sorted_tables)
    if table_names:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    from app.core.database import engine
    from sqlmodel import Session

    with Session(engine) as session:
        yield session


@pytest.fixture()
def make_user(db_session):
    """Creates a user directly against the repository, bypassing the API —
    there is no public registration endpoint by design (RN-REQ001-05), and
    the very first user (the superadministrator) has no authenticated admin
    to create it through `POST /users/` in the first place."""
    from app.core.security import derive_initial_password, hash_password
    from app.domain.entities.user import User, UserRole, UserStatus
    from app.infrastructure.repositories.user_repository_sql import SqlUserRepository

    repository = SqlUserRepository(db_session)

    def _make_user(
        full_name: str,
        document: str,
        role: "UserRole",
        status: "UserStatus" = UserStatus.ACTIVO,
        is_superadmin: bool = False,
    ) -> "User":
        user = User(
            full_name=full_name,
            document=document,
            hashed_password=hash_password(derive_initial_password(document)),
            role=role,
            status=status,
            is_superadmin=is_superadmin,
        )
        return repository.create(user)

    return _make_user


@pytest.fixture()
def token_for(client):
    """Logs a user in via the real API and returns an Authorization header
    dict, so tests exercise the actual login flow instead of forging JWTs."""

    def _token_for(document: str, password: str) -> dict[str, str]:
        response = client.post("/auth/login", json={"document": document, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _token_for


@pytest.fixture()
def auth_headers(make_user, token_for):
    """A ready-to-use Authorization header for an active operador, for tests
    that only need *some* authenticated user and don't care which role."""
    from app.domain.entities.user import UserRole

    document = "9999999999"
    make_user("Test Operator", document, UserRole.OPERADOR)
    return token_for(document, document[-4:])
