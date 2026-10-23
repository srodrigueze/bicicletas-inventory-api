import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES
from app.domain.entities.user import UserRole, UserStatus

DOCUMENT_PATTERN = re.compile(r"^\d{4,}$")

MASKED_DOCUMENT = "****"


class UserCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    document: str = Field(..., max_length=20)
    role: UserRole
    status: UserStatus = UserStatus.ACTIVO

    @field_validator("document")
    @classmethod
    def validate_document(cls, value: str) -> str:
        if not DOCUMENT_PATTERN.match(value):
            raise ValueError("document must contain only digits, with a minimum of 4")
        return value


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    status: UserStatus | None = None


class UserRead(BaseModel):
    id: int
    full_name: str
    document: str
    role: UserRole
    status: UserStatus
    is_superadmin: bool
    must_change_password: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    document: str = Field(..., max_length=20)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_length(cls, value: str) -> str:
        if len(value.encode()) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(f"new_password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes long")
        return value


class MessageResponse(BaseModel):
    detail: str
