from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Task, User
from app.utils import decode_access_token
from app.ai_agent import run_fraud_checks
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
# Auth Dependency
# --------------------------
def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# --------------------------
# Get task status
# --------------------------
@router.get("/{task_id}/status")
def task_status(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.id, "status": task.status, "user_id": task.user_id, "completed_at": task.completed_at}

# --------------------------
# Auto-approve tasks (run in scheduler)
# --------------------------
def auto_approve_pending_tasks():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        threshold = now - timedelta(hours=24)
        tasks = db.query(Task).filter(Task.status=="completed", Task.completed_at <= threshold).all()
        for task in tasks:
            task.status = "approved"
            # Credit user wallet
            user = db.query(User).filter(User.id==task.user_id).first()
            if user:
                user.wallet_balance += task.amount
            db.add(task)
            db.add(user)
            # Run fraud check
            run_fraud_checks(task)
        db.commit()
    finally:
        db.close()

# --------------------------
# Endpoint to trigger fraud scan manually
# --------------------------
@router.post("/fraud/scan")
def fraud_scan(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id==task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    run_fraud_checks(task)
    return {"status": "success", "message": f"Fraud scan completed for task {task_id}"}
