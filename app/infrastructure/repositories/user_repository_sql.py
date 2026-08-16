from sqlmodel import Session, select

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_document(self, document: str) -> User | None:
        statement = select(User).where(User.document == document)
        return self.session.exec(statement).first()

    def list_all(self, skip: int = 0, limit: int = 50) -> list[User]:
        statement = select(User).order_by(User.id).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

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
