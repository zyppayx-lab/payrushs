from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models import user
from app.schemas.user import UserCreate
from app.utils.auth import hash_password
import random, string

app = FastAPI()
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper: generate referral code
def generate_referral_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email or username exists
    if db.query(user.User).filter(user.User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(user.User).filter(user.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Hash password
    hashed_pw = hash_password(user_data.password)

    # Generate referral code
    code = generate_referral_code()

    # Create user
    new_user = user.User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_pw,
        referral_code=code,
        referred_by=user_data.referred_by
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "referral_code": new_user.referral_code
    }
