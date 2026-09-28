from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    restore = "restore"
    activate = "activate"
    deactivate = "deactivate"
    swap = "swap"  # no longer produced (swap removed 2026-09-28); kept so historical rows still parse
    returned = "returned"
    add_bicycle = "add_bicycle"


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    timestamp: datetime
    action: AuditAction
    entity_name: str = Field(max_length=50)
    entity_id: int
    previous_values: str | None = None
    new_values: str | None = None
