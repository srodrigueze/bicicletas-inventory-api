from collections.abc import Generator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

from app.core.config import settings

# NullPool: pooling is delegated to Neon's PgBouncer, not to SQLAlchemy.
engine = create_engine(settings.database_url, poolclass=NullPool)


def get_session() -> Generator[Session, None, None]:
    # expire_on_commit=False: a single request can commit more than once now
    # (e.g. the entity, then its audit log entry). The default would expire
    # every already-loaded object on each commit, forcing a reload on next
    # attribute access — repositories already call session.refresh() right
    # after their own commit when they need fresh state, so this only
    # removes the surprise expiration of *other* objects still in scope.
    with Session(engine, expire_on_commit=False) as session:
        yield session
