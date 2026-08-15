"""One-off CLI to create an admin user. There is no public registration endpoint
by design, so this is how the first (and any future) admin accounts get created.

Usage:
    python -m scripts.create_admin <username>
"""

import getpass
import sys

from sqlmodel import Session

from app.core.database import engine
from app.infrastructure.repositories.user_repository_sql import SqlUserRepository
from app.services.user_service import UserService


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.create_admin <username>")
        raise SystemExit(1)

    username = sys.argv[1]
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match")
        raise SystemExit(1)

    with Session(engine) as session:
        service = UserService(SqlUserRepository(session))
        user = service.create_user(username, password)
        print(f"Created user '{user.username}' (id={user.id})")


if __name__ == "__main__":
    main()
