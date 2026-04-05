from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
from app.database import SessionLocal
from app.models import User, Withdrawal, Task, Ledger
from app.utils import decode_access_token
from app.notifications import push_notification
from fastapi import Header

router = APIRouter()

# --------------------------
# DB Dependency
# --------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------
# Admin Auth Dependency
# --------------------------
def get_current_admin(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if not payload or "admin_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    # In production, you can add a proper admin table check
    return {"admin_id": payload["admin_id"]}

# --------------------------
# Approve Withdrawal
# --------------------------
@router.post("/withdrawals/{withdrawal_id}/approve")
def approve_withdrawal(withdrawal_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id==withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if withdrawal.status != "pending":
        raise HTTPException(status_code=400, detail="Withdrawal not pending")

    # Mark approved
    withdrawal.status = "approved"
    db.add(withdrawal)
    db.commit()
    push_notification(withdrawal.user_id, f"Your withdrawal of {float(withdrawal.amount)} Naira has been approved!")
    return {"status": "success", "message": f"Withdrawal {withdrawal_id} approved"}

# --------------------------
# Deny Withdrawal
# --------------------------
@router.post("/withdrawals/{withdrawal_id}/deny")
def deny_withdrawal(withdrawal_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id==withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if withdrawal.status != "pending":
        raise HTTPException(status_code=400, detail="Withdrawal not pending")

    # Refund user wallet
    user = db.query(User).filter(User.id==withdrawal.user_id).first()
    if user:
        user.wallet_balance += withdrawal.amount + withdrawal.fee
        db.add(user)
    withdrawal.status = "denied"
    db.add(withdrawal)
    db.commit()
    push_notification(withdrawal.user_id, f"Your withdrawal request has been denied and amount refunded.")
    return {"status": "success", "message": f"Withdrawal {withdrawal_id} denied and refunded"}

# --------------------------
# Approve Task
# --------------------------
@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    task = db.query(Task).filter(Task.id==task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task not completed or already approved")

    task.status = "approved"
    # Credit user wallet
    user = db.query(User).filter(User.id==task.user_id).first()
    if user:
        user.wallet_balance += task.amount
        db.add(user)
    db.add(task)
    db.commit()
    push_notification(task.user_id, f"Your task '{task.title}' has been approved by admin!")
    return {"status": "success", "message": f"Task {task_id} approved"}

# --------------------------
# Admin Analytics Dashboard
# --------------------------
@router.get("/analytics")
def analytics(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    total_users = db.query(User).count()
    total_tasks = db.query(Task).count()
    total_withdrawals = db.query(Withdrawal).filter(Withdrawal.status=="approved").all()
    total_payout = sum([w.amount for w in total_withdrawals])
    today = datetime.utcnow().date()
    today_users = db.query(User).filter(User.created_at >= today).count()
    today_tasks = db.query(Task).filter(Task.created_at >= today).count()
    today_ledger = db.query(Ledger).filter(Ledger.created_at >= today).all()
    today_platform_earnings = sum([abs(l.amount) for l in today_ledger if l.type=="deposit_fee" or l.type=="withdrawal_fee"])

    return {
        "total_users": total_users,
        "today_new_users": today_users,
        "total_tasks": total_tasks,
        "today_tasks": today_tasks,
        "total_payout": float(total_payout),
        "platform_earnings_today": float(today_platform_earnings)
    }
