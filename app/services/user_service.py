from app.core.security import create_access_token, hash_password, verify_password
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.schemas.user import UserRead


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def _to_read(self, user: User) -> UserRead:
        return UserRead(**user.model_dump())

    def list_users(self) -> list[UserRead]:
        return [self._to_read(user) for user in self.user_repository.list_all()]

    def get_user(self, user_id: int) -> UserRead | None:
        user = self.user_repository.get_by_id(user_id)
        return self._to_read(user) if user else None

    def create_user(self, username: str, password: str) -> UserRead:
        if self.user_repository.get_by_username(username):
            raise ValueError(f"A user with username '{username}' already exists")
        user = User(username=username, hashed_password=hash_password(password))
        created = self.user_repository.create(user)
        return self._to_read(created)

    def delete_user(self, user_id: int) -> None:
        self.user_repository.delete(user_id)

    def login(self, username: str, password: str) -> str | None:
        user = self.user_repository.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return create_access_token(subject=user.username)
