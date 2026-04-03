from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Backend is running 🚀"}


@app.get("/test-db")
def test_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "Database connected ✅"}
    except Exception as e:
        return {"error": str(e)}
