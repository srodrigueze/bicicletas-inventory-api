from collections.abc import Generator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

from app.core.config import settings

# NullPool: pooling is delegated to Neon's PgBouncer, not to SQLAlchemy.
engine = create_engine(settings.database_url, poolclass=NullPool)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
