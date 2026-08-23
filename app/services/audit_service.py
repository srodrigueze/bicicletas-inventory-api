from app.domain.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead


class AuditService:
    def __init__(self, audit_repository: AuditRepository):
        self.audit_repository = audit_repository

    def list_logs(self, *, skip: int = 0, limit: int = 50) -> list[AuditLogRead]:
        logs = self.audit_repository.list_all(skip=skip, limit=limit)
        return [AuditLogRead.model_validate(log) for log in logs]
