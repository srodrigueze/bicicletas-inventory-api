from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AuditServiceDep, CurrentUserDep
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("/", response_model=list[AuditLogRead])
def list_audit_logs(
    current_user: CurrentUserDep,
    service: AuditServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    start_date: date | None = Query(default=None, description="Un solo valor filtra ese día completo"),
    end_date: date | None = Query(default=None),
    user_id: int | None = Query(default=None),
    entity_name: str | None = Query(default=None),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_date must not be after end_date"
        )
    return service.list_logs(
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        entity_name=entity_name,
    )
