from fastapi import FastAPI, HTTPException, Request, status
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

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
    # Every response is private, per-user data (or a PDF report): never cacheable.
    response.headers.setdefault("Cache-Control", "no-store")
    return response


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
