import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import User, Task, Ledger
from app.notifications import push_notification
from app.utils import decimal_round
import redis
import os

# --------------------------
# Logging
# --------------------------
logger = logging.getLogger("ai-agent")

# --------------------------
# Upstash Redis connection
# --------------------------
REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None

# --------------------------
# Fraud Detection Function
# --------------------------
def run_fraud_checks():
    db: Session = SessionLocal()
    try:
        # 1️⃣ Detect duplicate accounts by phone or email
        users = db.query(User).all()
        seen_emails = {}
        seen_phones = {}
        for u in users:
            if u.email in seen_emails:
                flag_user(u, reason="Duplicate email")
            else:
                seen_emails[u.email] = u.id

            if u.phone_number in seen_phones:
                flag_user(u, reason="Duplicate phone number")
            else:
                seen_phones[u.phone_number] = u.id

        # 2️⃣ Detect suspicious deposits/withdrawals
        # Example: deposits > 500k Naira in single transaction or withdrawal > 50% of wallet
        for u in users:
            if u.last_deposit_amount and u.last_deposit_amount > 500_000:
                flag_user(u, reason="Large deposit detected")
            if u.last_withdrawal_amount and u.last_withdrawal_amount > (u.wallet_balance * 0.5):
                flag_user(u, reason="Suspicious withdrawal")

        # 3️⃣ Task farming / bot detection
        recent_tasks = db.query(Task).filter(
            Task.status=="completed",
            Task.submitted_at >= datetime.utcnow() - timedelta(hours=1)
        ).all()

        user_task_count = {}
        for t in recent_tasks:
            user_task_count[t.user_id] = user_task_count.get(t.user_id, 0) + 1

        for user_id, count in user_task_count.items():
            if count > 5:  # More than 5 tasks submitted in last hour
                user = db.query(User).filter(User.id == user_id).first()
                flag_user(user, reason="Possible bot activity")

        db.commit()
        logger.info("Fraud scan completed.")
    finally:
        db.close()

# --------------------------
# Helper to Flag Users
# --------------------------
def flag_user(user: User, reason: str):
    if not user:
        return
    user.is_flagged = True
    push_notification(user.id, f"⚠️ Your account has been flagged for: {reason}")
    # Hold wallet funds in escrow
    user.escrow_balance += user.wallet_balance
    user.wallet_balance = 0
    return user
