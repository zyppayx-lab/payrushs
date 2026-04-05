import os
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from decimal import Decimal, ROUND_HALF_UP

from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXP_MINUTES, FERNET_KEY

# --------------------------
# Password Hashing
# --------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

# --------------------------
# JWT Token Utilities
# --------------------------
def create_access_token(data: dict, expires_minutes: int = JWT_EXP_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

# --------------------------
# Fernet Encryption / Decryption
# --------------------------
fernet = Fernet(FERNET_KEY.encode())

def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

# --------------------------
# Decimal Money Handling
# --------------------------
def to_decimal(amount) -> Decimal:
    """Ensure all money amounts use Decimal with 2 decimal places"""
    return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
