from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import decode_access_token
from app.domain.entities.user import User, UserRole, UserStatus
from app.infrastructure.repositories.bicycle_repository_sql import SqlBicycleRepository
from app.infrastructure.repositories.loan_repository_sql import SqlLoanRepository
from app.infrastructure.repositories.user_repository_sql import SqlUserRepository
from app.services.bicycle_service import BicycleService
from app.services.loan_service import LoanService
from app.services.user_service import UserService

SessionDep = Annotated[Session, Depends(get_session)]


def get_bicycle_repository(session: SessionDep) -> SqlBicycleRepository:
    return SqlBicycleRepository(session)


def get_loan_repository(session: SessionDep) -> SqlLoanRepository:
    return SqlLoanRepository(session)


def get_user_repository(session: SessionDep) -> SqlUserRepository:
    return SqlUserRepository(session)


BicycleRepositoryDep = Annotated[SqlBicycleRepository, Depends(get_bicycle_repository)]
LoanRepositoryDep = Annotated[SqlLoanRepository, Depends(get_loan_repository)]
UserRepositoryDep = Annotated[SqlUserRepository, Depends(get_user_repository)]


def get_bicycle_service(
    bicycle_repository: BicycleRepositoryDep,
    loan_repository: LoanRepositoryDep,
) -> BicycleService:
    return BicycleService(bicycle_repository, loan_repository)


def get_loan_service(
    loan_repository: LoanRepositoryDep,
    bicycle_repository: BicycleRepositoryDep,
) -> LoanService:
    return LoanService(loan_repository, bicycle_repository)


def get_user_service(user_repository: UserRepositoryDep) -> UserService:
    return UserService(user_repository)


BicycleServiceDep = Annotated[BicycleService, Depends(get_bicycle_service)]
LoanServiceDep = Annotated[LoanService, Depends(get_loan_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


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


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    user_repository: UserRepositoryDep,
) -> User:
    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise _INVALID_TOKEN_EXCEPTION
    try:
        user_id = int(subject)
    except ValueError:
        raise _INVALID_TOKEN_EXCEPTION from None
    user = user_repository.get_by_id(user_id)
    # Re-checked on every request (not just at login time) so that
    # deactivating a user immediately revokes access, even mid-session.
    if user is None or user.status != UserStatus.ACTIVO:
        raise _INVALID_TOKEN_EXCEPTION
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_administrador(current_user: CurrentUserDep) -> User:
    if current_user.role != UserRole.ADMINISTRADOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return current_user


AdminUserDep = Annotated[User, Depends(require_administrador)]
