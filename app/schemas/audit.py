from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.entities.audit_log import AuditAction


class AuditLogRead(BaseModel):
    id: int
    user_id: int
    timestamp: datetime
    action: AuditAction
    entity_name: str
    entity_id: int
    previous_values: str | None
    new_values: str | None

    model_config = ConfigDict(from_attributes=True)
