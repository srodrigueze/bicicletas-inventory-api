import json
from datetime import datetime, timezone

from app.domain.entities.audit_log import AuditAction, AuditLog
from app.domain.entities.user import User
from app.domain.repositories.audit_repository import AuditRepository


def record_audit(
    audit_repository: AuditRepository,
    *,
    user: User,
    action: AuditAction,
    entity_name: str,
    entity_id: int,
    previous_values: dict | None,
    new_values: dict | None,
) -> None:
    audit_repository.create(
        AuditLog(
            user_id=user.id,
            timestamp=datetime.now(timezone.utc),
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            previous_values=json.dumps(previous_values) if previous_values is not None else None,
            new_values=json.dumps(new_values) if new_values is not None else None,
        )
    )
