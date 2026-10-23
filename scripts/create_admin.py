"""One-off CLI to create the seed superadministrator account. There is no
public registration endpoint by design (RN-REQ001-05): every other user is
created afterwards through the protected `POST /users/` endpoint by an
already-authenticated administrator. This script exists only to bootstrap
the single superadministrator (RN-REQ001-13), and refuses to run if one
already exists.

Usage:
    python -m scripts.create_admin <full_name> <document>

The initial password is set automatically (RNG-06) — it is not prompted, nor
printed. The account must change it at its first login.
"""

import sys

from sqlmodel import Session

from app.core.database import engine
from app.core.security import derive_initial_password, hash_password
from app.domain.entities.user import User, UserRole, UserStatus
from app.infrastructure.repositories.user_repository_sql import SqlUserRepository


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_admin <full_name> <document>")
        raise SystemExit(1)

    full_name = sys.argv[1]
    document = sys.argv[2]
    if not document.isdigit() or len(document) < 4:
        print("Document must contain only digits, with a minimum of 4")
        raise SystemExit(1)

    with Session(engine) as session:
        repository = SqlUserRepository(session)

        if repository.get_by_document(document):
            print(f"A user with document '{document}' already exists")
            raise SystemExit(1)

        existing_superadmin = next((u for u in repository.list_all() if u.is_superadmin), None)
        if existing_superadmin:
            print(
                f"A superadministrator already exists (id={existing_superadmin.id}); "
                "only one is allowed in the system"
            )
            raise SystemExit(1)

        initial_password = derive_initial_password(document)
        user = User(
            full_name=full_name,
            document=document,
            hashed_password=hash_password(initial_password),
            role=UserRole.ADMINISTRADOR,
            status=UserStatus.ACTIVO,
            is_superadmin=True,
        )
        created = repository.create(user)
        print(f"Created superadministrator '{created.full_name}' (id={created.id}, document={created.document})")


if __name__ == "__main__":
    main()
