from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    ADMINISTRADOR = "administrador"
    OPERADOR = "operador"


class UserStatus(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=150)
    document: str = Field(max_length=20, unique=True, index=True)
    hashed_password: str
    role: UserRole
    status: UserStatus = Field(default=UserStatus.ACTIVO)
    # Only meaningful when role == ADMINISTRADOR. At most one user in the whole
    # system can have this set to True, and it's immutable after creation (no
    # API action grants/revokes it) — see RN-REQ001-13.
    is_superadmin: bool = Field(default=False)
    # The initial password is derived from the document (RNG-06), so it is
    # guessable: every account starts with this flag on and can't use the API
    # (beyond changing its password) until it's cleared. Set again on reset.
    must_change_password: bool = Field(default=True)
    # Login throttling: consecutive failed attempts, and the moment until
    # which further attempts are refused once the limit is reached.
    failed_login_attempts: int = Field(default=0)
    # Bumped on every password change/reset; tokens carry the value they were
    # issued with, so older tokens stop working as soon as it changes.
    token_version: int = Field(default=0)
    locked_until: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
