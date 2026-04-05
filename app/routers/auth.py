from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.database import SessionLocal
from app.models import User, Vendor
from app.utils import hash_password, verify_password, create_access_token

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------
# User registration
# --------------------------
@router.post("/register/user")
def register_user(name: str, email: str, password: str, phone: str, referral_code: str = None, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email==email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(password)
    user = User(name=name, email=email, password=hashed_pw, phone=phone, referral_id=referral_code)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"user_id": user.id, "role": "user"})
    return {"access_token": token, "token_type": "bearer"}

# --------------------------
# Vendor registration
# --------------------------
@router.post("/register/vendor")
def register_vendor(name: str, email: str, password: str, phone: str, db: Session = Depends(get_db)):
    existing = db.query(Vendor).filter(Vendor.email==email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(password)
    vendor = Vendor(name=name, email=email, password=hashed_pw, phone=phone)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    token = create_access_token({"vendor_id": vendor.id, "role": "vendor"})
    return {"access_token": token, "token_type": "bearer"}

# --------------------------
# Login endpoint (user/vendor)
# --------------------------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username
    password = form_data.password
    # Check users
    user = db.query(User).filter(User.email==email).first()
    if user and verify_password(password, user.password):
        token = create_access_token({"user_id": user.id, "role": "user"})
        return {"access_token": token, "token_type": "bearer"}
    # Check vendors
    vendor = db.query(Vendor).filter(Vendor.email==email).first()
    if vendor and verify_password(password, vendor.password):
        token = create_access_token({"vendor_id": vendor.id, "role": "vendor"})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")
