from fastapi import FastAPI
from app.schemas.user import UserCreate
from app.models.user import User
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Optional: allow frontend to post requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register")
def register(user: UserCreate):
    # Example logic for testing
    return {"username": user.username, "email": user.email, "referral_code": "A1B2C3"}
