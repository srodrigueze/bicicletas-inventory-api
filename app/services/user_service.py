import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import (
    burn_password_check,
    create_access_token,
    derive_initial_password,
    hash_password,
    verify_password,
)
from app.domain.entities.audit_log import AuditAction
from app.domain.entities.user import User, UserRole, UserStatus
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.user_repository import UserRepository
from app.schemas.user import MASKED_DOCUMENT, UserCreate, UserRead, UserUpdate
from app.services.audit_recording import record_audit


class ForbiddenActionError(Exception):
    """Raised when the acting user lacks the permission required to perform
    an action over a target user (RN-REQ001-07, 14, 15, 16). The router
    translates this into a 403 response."""


class AccountLockedError(Exception):
    """Raised when a login is refused because the account hit the failed
    attempts limit. The router translates this into a 429 response."""

    def __init__(self, locked_until: datetime | None):
        self.locked_until = locked_until

    @property
    def retry_after_seconds(self) -> int:
        if self.locked_until is None:
            return settings.login_lock_minutes * 60
        remaining = (self.locked_until - datetime.now(timezone.utc)).total_seconds()
        return max(1, math.ceil(remaining))


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    must_change_password: bool


class UserService:
    def __init__(self, user_repository: UserRepository, audit_repository: AuditRepository):
        self.user_repository = user_repository
        self.audit_repository = audit_repository

    def _audit_snapshot(self, user: User) -> dict:
        data = user.model_dump(mode="json")
        data.pop("hashed_password", None)
        # Throttling bookkeeping, not business data: would only add noise to the audit trail.
        data.pop("failed_login_attempts", None)
        data.pop("locked_until", None)
        return data

    def _to_read(self, user: User) -> UserRead:
        document = MASKED_DOCUMENT if user.role == UserRole.ADMINISTRADOR else user.document
        return UserRead(
            id=user.id,
            full_name=user.full_name,
            document=document,
            role=user.role,
            status=user.status,
            is_superadmin=user.is_superadmin,
            must_change_password=user.must_change_password,
        )

    def list_users(self, skip: int = 0, limit: int = 50) -> list[UserRead]:
        return [self._to_read(user) for user in self.user_repository.list_all(skip=skip, limit=limit)]

    def get_user(self, user_id: int) -> UserRead | None:
        user = self.user_repository.get_by_id(user_id)
        return self._to_read(user) if user else None

    def get_self(self, user: User) -> UserRead:
        return self._to_read(user)

    def create_user(self, acting_user: User, data: UserCreate) -> UserRead:
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
            must_change_password=True,
        )

        created = self.user_repository.create(user)
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.create,
            entity_name="User",
            entity_id=created.id,
            previous_values=None,
            new_values=self._audit_snapshot(created),
        )
        return self._to_read(created)

    def _check_management_permission(self, acting_user: User, target: User) -> None:
        if target.id == acting_user.id:
            raise ForbiddenActionError("A user cannot modify or deactivate their own account")
        
        if target.role == UserRole.ADMINISTRADOR and not acting_user.is_superadmin:
            raise ForbiddenActionError("Only the superadministrator can manage another administrator")
        

    def update_user(self, acting_user: User, target_user_id: int, data: UserUpdate) -> UserRead | None:
        target = self.user_repository.get_by_id(target_user_id)
        if not target:
            return None

        self._check_management_permission(acting_user, target)
        update_data = data.model_dump(exclude_unset=True)
        previous_snapshot = self._audit_snapshot(target)
        status_changed = "status" in update_data and update_data["status"] != target.status

        for field, value in update_data.items():
            setattr(target, field, value)

        updated = self.user_repository.update(target)

        action = AuditAction.update
        if status_changed:
            action = AuditAction.activate if updated.status == UserStatus.ACTIVO else AuditAction.deactivate
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=action,
            entity_name="User",
            entity_id=updated.id,
            previous_values=previous_snapshot,
            new_values=self._audit_snapshot(updated),
        )
        return self._to_read(updated)
    

    def reset_password(self, acting_user: User, target_user_id: int) -> UserRead:
        target = self.user_repository.get_by_id(target_user_id)
        if not target:
            raise LookupError("User not found")
        
        self._check_management_permission(acting_user, target)
        derived = derive_initial_password(target.document)
        target.hashed_password = hash_password(derived)
        target.must_change_password = True
        target.token_version += 1
        # A reset is also how an administrator unlocks a locked-out account.
        target.failed_login_attempts = 0
        target.locked_until = None
        updated = self.user_repository.update(target)
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.password_reset,
            entity_name="User",
            entity_id=updated.id,
            previous_values=None,
            new_values=None,
        )
        return self._to_read(updated)


    def change_password(self, current_user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, current_user.hashed_password):
            raise ValueError("Current password is incorrect")

        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters long")

        current_user.hashed_password = hash_password(new_password)
        current_user.must_change_password = False
        current_user.token_version += 1
        self.user_repository.update(current_user)
        record_audit(
            self.audit_repository,
            user=current_user,
            action=AuditAction.password_change,
            entity_name="User",
            entity_id=current_user.id,
            previous_values=None,
            new_values=None,
        )


    def login(self, document: str, password: str) -> LoginResult | None:
        user = self.user_repository.get_by_document(document)
        if not user or user.status != UserStatus.ACTIVO:
            burn_password_check(password)
            return None

        # The attempt is counted *before* checking the password, so concurrent
        # guesses are all accounted for and a locked account never even gets
        # its password verified.
        now = datetime.now(timezone.utc)
        attempts, locked_until = self.user_repository.register_login_attempt(
            user.id,
            max_attempts=settings.login_max_attempts,
            lock_until=now + timedelta(minutes=settings.login_lock_minutes),
            now=now,
        )
        if attempts > settings.login_max_attempts:
            raise AccountLockedError(locked_until)

        if not verify_password(password, user.hashed_password):
            return None

        self.user_repository.reset_login_attempts(user.id)
        return LoginResult(
            access_token=create_access_token(subject=str(user.id), token_version=user.token_version),
            must_change_password=user.must_change_password,
        )
