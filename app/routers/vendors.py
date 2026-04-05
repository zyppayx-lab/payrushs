from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List
from app.database import SessionLocal
from app.models import Vendor, Task, Ledger, User
from app.utils import safe_add, decode_access_token
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
# Auth Dependency
# --------------------------
def get_current_vendor(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if not payload or "vendor_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    vendor = db.query(Vendor).filter(Vendor.id == payload["vendor_id"]).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

# --------------------------
# Create / Fund Task (escrow)
# --------------------------
@router.post("/tasks/create")
def create_task(title: str, description: str, amount: Decimal, current_vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Task amount must be positive")
    task = Task(
        title=title,
        description=description,
        amount=amount,
        vendor_id=current_vendor.id,
        status="pending"
    )
    db.add(task)
    # Deduct vendor wallet (escrow)
    if current_vendor.wallet_balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient vendor balance")
    current_vendor.wallet_balance -= amount
    # Ledger entry
    ledger_entry = Ledger(
        vendor_id=current_vendor.id,
        amount=-amount,
        type="escrow",
        reference=f"escrow_task_{task.title}"
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(task)
    return {"status": "success", "task_id": task.id, "title": task.title, "amount": float(amount)}

# --------------------------
# View vendor tasks
# --------------------------
@router.get("/tasks")
def view_tasks(current_vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.vendor_id==current_vendor.id).all()
    return [{"id": t.id, "title": t.title, "amount": float(t.amount), "status": t.status, "user_id": t.user_id} for t in tasks]

# --------------------------
# Approve task submission
# --------------------------
@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: int, current_vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id==task_id, Task.vendor_id==current_vendor.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
    task.status = "approved"
    # Credit user wallet
    user = db.query(User).filter(User.id==task.user_id).first()
    if user:
        user.wallet_balance = safe_add(user.wallet_balance, task.amount)
        db.add(user)
        push_notification(user.id, f"Your task '{task.title}' has been approved! {float(task.amount)} Naira credited.")
    db.add(task)
    db.commit()
    return {"status": "success", "message": f"Task '{task.title}' approved and user credited."}
