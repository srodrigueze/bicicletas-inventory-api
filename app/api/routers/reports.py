from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import AdminUserDep, ReportServiceDep

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/loans")
def get_loans_report(
    admin: AdminUserDep,
    service: ReportServiceDep,
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    try:
        pdf_bytes = service.generate_loans_report(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    filename = f"reporte_prestamos_{start_date.isoformat()}_{end_date.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
