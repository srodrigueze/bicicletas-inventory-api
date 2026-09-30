from datetime import datetime

from sqlmodel import Session, select

from app.domain.entities.audit_log import AuditLog
from app.domain.repositories.audit_repository import AuditRepository


class SqlAuditRepository(AuditRepository):
    def __init__(self, session: Session):
        self.session = session

    def create(self, log: AuditLog) -> AuditLog:
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        user_id: int | None = None,
        entity_name: str | None = None,
    ) -> list[AuditLog]:
        statement = select(AuditLog)
        if start_datetime is not None:
            statement = statement.where(AuditLog.timestamp >= start_datetime)
        if end_datetime is not None:
            statement = statement.where(AuditLog.timestamp <= end_datetime)
        if user_id is not None:
            statement = statement.where(AuditLog.user_id == user_id)
        if entity_name is not None:
            statement = statement.where(AuditLog.entity_name == entity_name)
        statement = statement.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
