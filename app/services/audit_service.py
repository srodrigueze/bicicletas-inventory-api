from datetime import date

from app.core.timezone import day_bounds_utc
from app.domain.entities.audit_log import AuditLog
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.bicycle_repository import BicycleRepository
from app.domain.repositories.user_repository import UserRepository
from app.schemas.audit import AuditLogRead


class AuditService:
    def __init__(
        self,
        audit_repository: AuditRepository,
        user_repository: UserRepository,
        bicycle_repository: BicycleRepository,
    ):
        self.audit_repository = audit_repository
        self.user_repository = user_repository
        self.bicycle_repository = bicycle_repository

    def _entity_reference(self, log: AuditLog) -> str:
        # Bicycle.id (an internal auto-increment PK) means nothing to a
        # person reading the audit trail; its `code` is what was actually
        # typed in at registration time (HU-07) and is what the user
        # recognizes. Other entities (User, Loan) don't have an equivalent
        # user-facing identifier, so they fall back to the raw id.
        if log.entity_name == "Bicycle":
            bicycle = self.bicycle_repository.get_by_id(log.entity_id)
            if bicycle:
                return bicycle.code
        return str(log.entity_id)

    def _to_read(self, log: AuditLog) -> AuditLogRead:
        user = self.user_repository.get_by_id(log.user_id)
        return AuditLogRead(
            id=log.id,
            user_id=log.user_id,
            user_full_name=user.full_name if user else None,
            timestamp=log.timestamp,
            action=log.action,
            entity_name=log.entity_name,
            entity_id=log.entity_id,
            entity_reference=self._entity_reference(log),
            previous_values=log.previous_values,
            new_values=log.new_values,
        )

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
        return [self._to_read(log) for log in logs]
