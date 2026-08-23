from abc import ABC, abstractmethod

from app.domain.entities.audit_log import AuditLog


class AuditRepository(ABC):
    @abstractmethod
    def create(self, log: AuditLog) -> AuditLog: ...

    @abstractmethod
    def list_all(self, *, skip: int = 0, limit: int = 50) -> list[AuditLog]: ...
