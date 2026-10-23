from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.security import decode_access_token
from app.domain.entities.user import User, UserRole, UserStatus
from app.domain.repositories.image_storage_repository import ImageStorageRepository
from app.infrastructure.repositories.audit_repository_sql import SqlAuditRepository
from app.infrastructure.repositories.bicycle_repository_sql import SqlBicycleRepository
from app.infrastructure.repositories.client_repository_sql import SqlClientRepository
from app.infrastructure.repositories.loan_repository_sql import SqlLoanRepository
from app.infrastructure.repositories.user_repository_sql import SqlUserRepository
from app.services.audit_service import AuditService
from app.services.bicycle_service import BicycleService
from app.services.client_service import ClientService
from app.services.loan_service import LoanService
from app.services.report_service import ReportService
from app.services.user_service import UserService

SessionDep = Annotated[Session, Depends(get_session)]


def get_bicycle_repository(session: SessionDep) -> SqlBicycleRepository:
    return SqlBicycleRepository(session)


def get_loan_repository(session: SessionDep) -> SqlLoanRepository:
    return SqlLoanRepository(session)


def get_client_repository(session: SessionDep) -> SqlClientRepository:
    return SqlClientRepository(session)


def get_user_repository(session: SessionDep) -> SqlUserRepository:
    return SqlUserRepository(session)


def get_audit_repository(session: SessionDep) -> SqlAuditRepository:
    return SqlAuditRepository(session)


@lru_cache(maxsize=1)
def get_image_storage_repository() -> ImageStorageRepository:
    # The only place that knows which storage provider is in use. To support
    # another one, implement ImageStorageRepository and add a branch here.
    # Imported lazily so a provider's SDK is only needed when it's selected.
    if settings.storage_backend == "gcs":
        from app.infrastructure.repositories.gcs_image_storage_repository import GcsImageStorageRepository

        return GcsImageStorageRepository(settings.gcs_bucket_name)
    raise RuntimeError(f"Unsupported STORAGE_BACKEND: {settings.storage_backend!r}")


BicycleRepositoryDep = Annotated[SqlBicycleRepository, Depends(get_bicycle_repository)]
LoanRepositoryDep = Annotated[SqlLoanRepository, Depends(get_loan_repository)]
ClientRepositoryDep = Annotated[SqlClientRepository, Depends(get_client_repository)]
UserRepositoryDep = Annotated[SqlUserRepository, Depends(get_user_repository)]
AuditRepositoryDep = Annotated[SqlAuditRepository, Depends(get_audit_repository)]
ImageStorageRepositoryDep = Annotated[ImageStorageRepository, Depends(get_image_storage_repository)]


def get_bicycle_service(
    bicycle_repository: BicycleRepositoryDep,
    loan_repository: LoanRepositoryDep,
    audit_repository: AuditRepositoryDep,
    image_storage_repository: ImageStorageRepositoryDep,
) -> BicycleService:
    return BicycleService(bicycle_repository, loan_repository, audit_repository, image_storage_repository)


def get_loan_service(
    loan_repository: LoanRepositoryDep,
    bicycle_repository: BicycleRepositoryDep,
    client_repository: ClientRepositoryDep,
    audit_repository: AuditRepositoryDep,
) -> LoanService:
    return LoanService(loan_repository, bicycle_repository, client_repository, audit_repository)


def get_client_service(client_repository: ClientRepositoryDep) -> ClientService:
    return ClientService(client_repository)


def get_user_service(
    user_repository: UserRepositoryDep,
    audit_repository: AuditRepositoryDep,
) -> UserService:
    return UserService(user_repository, audit_repository)


def get_audit_service(
    audit_repository: AuditRepositoryDep,
    user_repository: UserRepositoryDep,
    bicycle_repository: BicycleRepositoryDep,
) -> AuditService:
    return AuditService(audit_repository, user_repository, bicycle_repository)


def get_report_service(
    loan_repository: LoanRepositoryDep,
    client_repository: ClientRepositoryDep,
    bicycle_repository: BicycleRepositoryDep,
) -> ReportService:
    return ReportService(loan_repository, client_repository, bicycle_repository)


BicycleServiceDep = Annotated[BicycleService, Depends(get_bicycle_service)]
LoanServiceDep = Annotated[LoanService, Depends(get_loan_service)]
ClientServiceDep = Annotated[ClientService, Depends(get_client_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


# --- Auth guards -------------------------------------------------------
# Cross-cutting concern (HU-02: every protected endpoint requires a valid
# JWT), not resource-specific business logic, so it's implemented as a
# FastAPI dependency here rather than inside UserService. Uses HTTPBearer
# (not OAuth2PasswordBearer) because /auth/login takes a JSON body
# (document/password), not an OAuth2 form.
bearer_scheme = HTTPBearer()

_INVALID_TOKEN_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    user_repository: UserRepositoryDep,
) -> User:
    claims = decode_access_token(credentials.credentials)
    if claims is None:
        raise _INVALID_TOKEN_EXCEPTION
    try:
        user_id = int(claims.subject)
    except ValueError:
        raise _INVALID_TOKEN_EXCEPTION from None
    user = user_repository.get_by_id(user_id)
    # Re-checked on every request (not just at login time) so that
    # deactivating a user immediately revokes access, even mid-session.
    if user is None or user.status != UserStatus.ACTIVO:
        raise _INVALID_TOKEN_EXCEPTION
    # A password change/reset bumps token_version, revoking every token
    # issued before it (e.g. one stolen before the user changed their password).
    if claims.version != user.token_version:
        raise _INVALID_TOKEN_EXCEPTION
    return user


# Valid token, active user — even if they still must change their password.
# Only the endpoints needed to do that (change-password, /users/me) use this.
AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]


def get_current_user(user: AuthenticatedUserDep) -> User:
    # The initial password is derived from the document, so it is guessable:
    # until it's changed the account can do nothing else.
    if user.must_change_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password change required")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_administrador(current_user: CurrentUserDep) -> User:
    if current_user.role != UserRole.ADMINISTRADOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return current_user


AdminUserDep = Annotated[User, Depends(require_administrador)]
