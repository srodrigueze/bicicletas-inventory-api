from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from app.api.deps import SessionDep
from app.api.routers import audits, auth, bicycles, clients, loans, reports, users
from app.core.config import settings

app = FastAPI(
    title="Bicycle Loan Inventory API",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

app.include_router(bicycles.router)
app.include_router(loans.router)
app.include_router(clients.router)
app.include_router(audits.router)
app.include_router(reports.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def health_check(session: SessionDep):
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unreachable"
        ) from exc
    return {"status": "ok"}
