from sqlalchemy import Column, Integer, String
from app.utils.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    referral_code = Column(String, unique=True)
    referred_by = Column(Integer, nullable=True)
