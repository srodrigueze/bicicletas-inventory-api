from fastapi import APIRouter, HTTPException, status

from app.api.deps import UserServiceDep
from app.schemas.user import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: UserServiceDep):
    token = service.login(data.document, data.password)
    if not token:
        # RN-REQ001-09 / HU-01: same generic message for invalid credentials
        # and for an inactive account, never revealing which one failed.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=token)
