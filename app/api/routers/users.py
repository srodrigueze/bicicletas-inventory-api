from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUserDep, CurrentUserDep, UserServiceDep
from app.schemas.user import MessageResponse, PasswordChangeRequest, UserCreate, UserRead, UserUpdate
from app.services.user_service import ForbiddenActionError

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/change-password", response_model=MessageResponse)
def change_my_password(data: PasswordChangeRequest, current_user: CurrentUserDep, service: UserServiceDep):
    try:
        service.change_password(current_user, data.current_password, data.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(detail="Password updated")


@router.get("/", response_model=list[UserRead])
def list_users(
    admin: AdminUserDep,
    service: UserServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    # RNG-05 / HU-06: every list in every panel must be paginated.
    return service.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, admin: AdminUserDep, service: UserServiceDep):
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, admin: AdminUserDep, service: UserServiceDep):
    try:
        return service.create_user(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, admin: AdminUserDep, service: UserServiceDep):
    try:
        user = service.update_user(acting_user=admin, target_user_id=user_id, data=data)
    except ForbiddenActionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_password(user_id: int, admin: AdminUserDep, service: UserServiceDep):
    try:
        return service.reset_password(acting_user=admin, target_user_id=user_id)
    except ForbiddenActionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
