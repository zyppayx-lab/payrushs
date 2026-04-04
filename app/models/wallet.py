from sqlalchemy import Column, Integer, Float, String, ForeignKey
from app.utils.database import Base

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Float, default=0)
    currency = Column(String, default="NGN")
