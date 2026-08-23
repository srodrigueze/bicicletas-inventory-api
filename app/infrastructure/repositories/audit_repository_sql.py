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

    def list_all(self, *, skip: int = 0, limit: int = 50) -> list[AuditLog]:
        statement = select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
