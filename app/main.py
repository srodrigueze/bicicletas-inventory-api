from fastapi import FastAPI

from app.api.routers import auth, bicycles, loans

app = FastAPI(title="Bicycle Loan Inventory API")

app.include_router(bicycles.router)
app.include_router(loans.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    return {"message": "Bicycle loan inventory API is running"}
