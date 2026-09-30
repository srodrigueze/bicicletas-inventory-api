from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.audit_log import AuditLog


class AuditRepository(ABC):
    @abstractmethod
    def create(self, log: AuditLog) -> AuditLog: ...

    @abstractmethod
    def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        user_id: int | None = None,
        entity_name: str | None = None,
    ) -> list[AuditLog]: ...
