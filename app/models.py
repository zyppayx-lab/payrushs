from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# --------------------------
# Users
# --------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    email = Column(String(150), unique=True, index=True)
    phone_number = Column(String(50))
    password_hash = Column(String(255))
    wallet_balance = Column(Numeric(12,2), default=0)
    has_received_signup_bonus = Column(Boolean, default=False)
    referral_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_earned = Column(Numeric(12,2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_flagged = Column(Boolean, default=False)

    referrals = relationship("User", remote_side=[id])
    tasks = relationship("Task", back_populates="user")
    ledgers = relationship("Ledger", back_populates="user")


# --------------------------
# Vendors
# --------------------------
class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    email = Column(String(150), unique=True)
    phone_number = Column(String(50))
    password_hash = Column(String(255))
    total_earned = Column(Numeric(12,2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_flagged = Column(Boolean, default=False)

    tasks = relationship("Task", back_populates="vendor")


# --------------------------
# Tasks & Escrow
# --------------------------
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    description = Column(Text)
    amount = Column(Numeric(12,2))
    status = Column(String(50), default="pending")  # pending, completed, approved, rejected
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    proof_screenshot = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    is_flagged = Column(Boolean, default=False)

    user = relationship("User", back_populates="tasks")
    vendor = relationship("Vendor", back_populates="tasks")


# --------------------------
# Ledger (double-entry)
# --------------------------
class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    amount = Column(Numeric(12,2))
    type = Column(String(50))  # deposit, withdrawal, task_credit, task_debit
    reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ledgers")


# --------------------------
# Withdrawals (manual)
# --------------------------
class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(12,2))
    bank_name = Column(String(150))
    account_number = Column(String(50))
    account_name = Column(String(150))
    status = Column(String(50), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

# --------------------------
# Notifications
# --------------------------
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    title = Column(String(200))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
