from enum import Enum

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
