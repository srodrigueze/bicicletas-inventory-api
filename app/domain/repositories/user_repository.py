from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_document(self, document: str) -> User | None: ...

    @abstractmethod
    def list_all(self, skip: int = 0, limit: int = 50) -> list[User]: ...

    @abstractmethod
    def create(self, user: User) -> User: ...

    @abstractmethod
    def update(self, user: User) -> User: ...

    @abstractmethod
    def register_login_attempt(
        self, user_id: int, *, max_attempts: int, lock_until: datetime, now: datetime
    ) -> tuple[int, datetime | None]:
        """Atomically counts one login attempt and returns the new
        (attempt count, locked_until). A count above `max_attempts` means the
        account is locked and the attempt must be refused."""
        ...

    @abstractmethod
    def reset_login_attempts(self, user_id: int) -> None: ...

    @abstractmethod
    def delete(self, user_id: int) -> None: ...
