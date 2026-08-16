from app.core.security import create_access_token, derive_initial_password, hash_password, verify_password
from app.domain.entities.user import User, UserRole, UserStatus
from app.domain.repositories.user_repository import UserRepository
from app.schemas.user import MASKED_DOCUMENT, UserCreate, UserRead, UserUpdate


class ForbiddenActionError(Exception):
    """Raised when the acting user lacks the permission required to perform
    an action over a target user (RN-REQ001-07, 14, 15, 16). The router
    translates this into a 403 response."""


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def _to_read(self, user: User) -> UserRead:
        # RN-REQ001-08: the document of any user with role administrador is
        # always masked in API responses, regardless of who is asking.
        document = MASKED_DOCUMENT if user.role == UserRole.ADMINISTRADOR else user.document
        return UserRead(
            id=user.id,
            full_name=user.full_name,
            document=document,
            role=user.role,
            status=user.status,
            is_superadmin=user.is_superadmin,
        )

    def list_users(self, skip: int = 0, limit: int = 50) -> list[UserRead]:
        return [self._to_read(user) for user in self.user_repository.list_all(skip=skip, limit=limit)]

    def get_user(self, user_id: int) -> UserRead | None:
        user = self.user_repository.get_by_id(user_id)
        return self._to_read(user) if user else None

    def create_user(self, data: UserCreate) -> UserRead:
        if self.user_repository.get_by_document(data.document):
            raise ValueError(f"A user with document '{data.document}' already exists")
        initial_password = derive_initial_password(data.document)
        user = User(
            full_name=data.full_name,
            document=data.document,
            hashed_password=hash_password(initial_password),
            role=data.role,
            status=data.status,
            is_superadmin=False,  # RN-REQ001-13: never granted through this endpoint
        )
        created = self.user_repository.create(user)
        return self._to_read(created)

    def _check_management_permission(self, acting_user: User, target: User) -> None:
        # RN-REQ001-14: absolute, applies to every role/level, including the
        # superadministrator.
        if target.id == acting_user.id:
            raise ForbiddenActionError("A user cannot modify or deactivate their own account")
        # RN-REQ001-07 / RN-REQ001-15: only the superadministrator has power
        # over other administrators; a regular administrator has none.
        if target.role == UserRole.ADMINISTRADOR and not acting_user.is_superadmin:
            raise ForbiddenActionError("Only the superadministrator can manage another administrator")

    def update_user(self, acting_user: User, target_user_id: int, data: UserUpdate) -> UserRead | None:
        target = self.user_repository.get_by_id(target_user_id)
        if not target:
            return None
        self._check_management_permission(acting_user, target)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(target, field, value)
        updated = self.user_repository.update(target)
        return self._to_read(updated)

    def reset_password(self, acting_user: User, target_user_id: int) -> UserRead:
        target = self.user_repository.get_by_id(target_user_id)
        if not target:
            raise LookupError("User not found")
        # RN-REQ001-16: reset is a management action over the target user,
        # subject to the same hierarchy rules as edit/activate/deactivate.
        self._check_management_permission(acting_user, target)
        derived = derive_initial_password(target.document)
        target.hashed_password = hash_password(derived)
        updated = self.user_repository.update(target)
        return self._to_read(updated)

    def change_password(self, current_user: User, current_password: str, new_password: str) -> None:
        # RN-REQ001-18: current password must be re-entered.
        if not verify_password(current_password, current_user.hashed_password):
            raise ValueError("Current password is incorrect")
        # RN-REQ001-17: minimum length of 6 characters (also enforced by the schema).
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters long")
        current_user.hashed_password = hash_password(new_password)
        self.user_repository.update(current_user)

    def login(self, document: str, password: str) -> str | None:
        user = self.user_repository.get_by_document(document)
        if not user or user.status != UserStatus.ACTIVO:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return create_access_token(subject=str(user.id))
