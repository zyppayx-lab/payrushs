from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Task, User, Ledger
from app.notifications import push_notification
from app.utils import decimal_round

scheduler = BackgroundScheduler()

# --------------------------
# Auto-approve Tasks After 24h
# --------------------------
def auto_approve_tasks():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        pending_tasks = db.query(Task).filter(
            Task.status == "completed",
            Task.submitted_at <= now - timedelta(hours=24)
        ).all()

        for task in pending_tasks:
            task.status = "approved"

            # Credit user wallet
            user = db.query(User).filter(User.id == task.user_id).first()
            if user:
                user.wallet_balance += task.amount
                db.add(user)

            # Ledger entry
            ledger = Ledger(
                user_id=task.user_id,
                amount=task.amount,
                type="task_approval",
                reference=f"task-{task.id}",
                created_at=datetime.utcnow()
            )
            db.add(ledger)

            db.add(task)
            push_notification(task.user_id, f"Task '{task.title}' auto-approved! {decimal_round(task.amount)} Naira credited.")

        db.commit()
    finally:
        db.close()

# --------------------------
# Referral Bonus Check
# Users earn bonus after referred users complete 2 tasks
# --------------------------
def check_referral_bonus(user_id: int):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.referred_by:
            return

        # Count completed tasks of referred user
        completed_tasks = db.query(Task).filter(Task.user_id == user.id, Task.status=="approved").count()
        if completed_tasks >= 2 and not user.referral_bonus_given:
            referrer = db.query(User).filter(User.id == user.referred_by).first()
            if referrer:
                bonus_amount = 200  # Referral bonus
                referrer.wallet_balance += bonus_amount

                # Ledger entry
                ledger = Ledger(
                    user_id=referrer.id,
                    amount=bonus_amount,
                    type="referral_bonus",
                    reference=f"referral-{user.id}",
                    created_at=datetime.utcnow()
                )
                db.add(ledger)
                db.add(referrer)
                user.referral_bonus_given = True
                db.add(user)
                db.commit()
                push_notification(referrer.id, f"You earned {bonus_amount} Naira referral bonus from {user.name}!")

    finally:
        db.close()
