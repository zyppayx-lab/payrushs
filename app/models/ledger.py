from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from app.database import Base

class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)

    amount = Column(Float)
    type = Column(String)

    reference = Column(String, unique=True)
    description = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
