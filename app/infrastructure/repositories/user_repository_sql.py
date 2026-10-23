from datetime import datetime

from sqlalchemy import and_, case, null, update
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

    def register_login_attempt(
        self, user_id: int, *, max_attempts: int, lock_until: datetime, now: datetime
    ) -> tuple[int, datetime | None]:
        # One UPDATE ... RETURNING instead of read-modify-write: Postgres
        # serializes concurrent updates on the row, so parallel requests can't
        # all read the same counter and slip extra guesses past the limit.
        # Both SET expressions are evaluated against the pre-update row.
        lock_expired = and_(User.locked_until.is_not(None), User.locked_until <= now)
        new_attempts = case((lock_expired, 1), else_=User.failed_login_attempts + 1)
        new_locked_until = case(
            (lock_expired, null()),
            (and_(new_attempts >= max_attempts, User.locked_until.is_(None)), lock_until),
            else_=User.locked_until,
        )
        statement = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=new_attempts, locked_until=new_locked_until)
            .returning(User.failed_login_attempts, User.locked_until)
            .execution_options(synchronize_session=False)
        )
        attempts, locked_until = self.session.execute(statement).one()
        self.session.commit()
        return attempts, locked_until

    def reset_login_attempts(self, user_id: int) -> None:
        statement = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=0, locked_until=None)
            .execution_options(synchronize_session=False)
        )
        self.session.execute(statement)
        self.session.commit()

    def delete(self, user_id: int) -> None:
        user = self.session.get(User, user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
