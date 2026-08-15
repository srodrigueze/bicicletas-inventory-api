from sqlmodel import Session, select

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        return self.session.exec(statement).first()

    def list_all(self) -> list[User]:
        return list(self.session.exec(select(User)).all())

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete(self, user_id: int) -> None:
        user = self.session.get(User, user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
