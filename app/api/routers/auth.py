from fastapi import APIRouter, HTTPException, status

from app.api.deps import UserServiceDep
from app.schemas.user import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: UserServiceDep):
    token = service.login(data.username, data.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=token)
