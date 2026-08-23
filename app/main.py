from fastapi import FastAPI

from app.api.routers import audits, auth, bicycles, clients, loans, reports, users

app = FastAPI(title="Bicycle Loan Inventory API")

app.include_router(bicycles.router)
app.include_router(loans.router)
app.include_router(clients.router)
app.include_router(audits.router)
app.include_router(reports.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {"message": "Bicycle loan inventory API is running"}
