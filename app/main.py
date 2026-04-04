from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.utils.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.user import UserCreate, UserLogin
from app.utils.auth import hash_password, verify_password, create_access_token
import random, string

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_referral_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        password=hashed,
        referral_code=generate_referral_code(),
        referred_by=user.referred_by
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Step 2: Create wallet automatically
    wallet = Wallet(user_id=new_user.id)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return {"username": new_user.username, "email": new_user.email, "referral_code": new_user.referral_code}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"user_id": db_user.id})
    return {"access_token": token, "token_type": "bearer"}
