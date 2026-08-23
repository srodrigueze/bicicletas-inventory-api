from fastapi import APIRouter, Query

from app.api.deps import AuditServiceDep, CurrentUserDep
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("/", response_model=list[AuditLogRead])
def list_audit_logs(
    current_user: CurrentUserDep,
    service: AuditServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    return service.list_logs(skip=skip, limit=limit)
