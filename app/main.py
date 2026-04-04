from fastapi import FastAPI
from app.utils.database import Base, engine
from app.routers import user

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payrushs Backend")

app.include_router(user.router, prefix="/user", tags=["User"])

@app.get("/")
def root():
    return {"status": "Backend is live ✅"}

@app.get("/health")
def health():
    return {"status": "Backend alive and database ready ✅"}
