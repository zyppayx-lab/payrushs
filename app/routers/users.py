from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import SessionLocal
from app.models import User, Task, Ledger
from app.utils import safe_add, safe_sub, decode_access_token
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
# Browse tasks
# --------------------------
@router.get("/tasks")
def browse_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.status=="pending").all()
    return [{"id": t.id, "title": t.title, "amount": t.amount, "vendor": t.vendor.name} for t in tasks]

# --------------------------
# Submit task proof
# --------------------------
@router.post("/tasks/{task_id}/submit")
def submit_task(task_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id==task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id and task.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Task already claimed")
    # Save file
    upload_path = f"app/uploads/task_{task_id}_{file.filename}"
    with open(upload_path, "wb") as f:
        f.write(file.file.read())
    task.proof_file = upload_path
    task.user_id = current_user.id
    task.completed_at = task.completed_at or None
    task.status = "completed"
    db.add(task)
    db.commit()
    push_notification(task.vendor_id, f"{current_user.name} submitted proof for task '{task.title}'")
    return {"status": "success", "message": "Task submitted"}

# --------------------------
# View wallet
# --------------------------
@router.get("/wallet")
def view_wallet(current_user: User = Depends(get_current_user)):
    return {"wallet_balance": float(current_user.wallet_balance)}

# --------------------------
# Withdraw funds
# --------------------------
@router.post("/wallet/withdraw")
def withdraw(amount: Decimal, bank_account: str, bank_name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    MIN_WITHDRAW = Decimal(1000)
    FEE_RATE = Decimal("0.03")
    if amount < MIN_WITHDRAW:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is {MIN_WITHDRAW} Naira")
    if amount > current_user.wallet_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    net_amount = amount - (amount * FEE_RATE)
    current_user.wallet_balance = safe_sub(current_user.wallet_balance, amount)
    from app.models import Ledger
    ledger_entry = Ledger(
        user_id=current_user.id,
        amount=-amount,
        type="withdrawal",
        reference=f"withdraw_{bank_account}_{int(Decimal(amount))}"
    )
    db.add(ledger_entry)
    db.commit()
    push_notification(current_user.id, f"Withdrawal of {net_amount} Naira requested. Awaiting admin approval.")
    return {"status": "success", "requested_amount": float(amount), "net_amount": float(net_amount)}

# --------------------------
# Leaderboard
# --------------------------
@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.wallet_balance.desc()).limit(10).all()
    return [{"name": u.name, "balance": float(u.wallet_balance)} for u in users]
