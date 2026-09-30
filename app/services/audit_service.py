from datetime import date

from app.core.timezone import day_bounds_utc
from app.domain.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead


class AuditService:
    def __init__(self, audit_repository: AuditRepository):
        self.audit_repository = audit_repository

    def list_logs(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        start_date: date | None = None,
        end_date: date | None = None,
        user_id: int | None = None,
        entity_name: str | None = None,
    ) -> list[AuditLogRead]:
        # A single date filters that one day: passing only one of the two
        # bounds is treated as "just that day", same convention as RNG-22
        # (report date ranges always span a full local day, 00:00 to 23:59).
        if start_date and not end_date:
            end_date = start_date
        elif end_date and not start_date:
            start_date = end_date

        start_datetime = day_bounds_utc(start_date)[0] if start_date else None
        end_datetime = day_bounds_utc(end_date)[1] if end_date else None

        logs = self.audit_repository.list_all(
            skip=skip,
            limit=limit,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            user_id=user_id,
            entity_name=entity_name,
        )
        return [AuditLogRead.model_validate(log) for log in logs]
