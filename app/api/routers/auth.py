from fastapi import APIRouter, HTTPException, status

from app.api.deps import UserServiceDep
from app.schemas.user import LoginRequest, TokenResponse
from app.services.user_service import AccountLockedError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: UserServiceDep):
    try:
        result = service.login(data.document, data.password)
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts, try again later",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(access_token=result.access_token, must_change_password=result.must_change_password)
