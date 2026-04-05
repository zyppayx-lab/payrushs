from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from fastapi import Header
from app.database import SessionLocal
from app.models import User, Ledger, Withdrawal
from app.utils import decode_access_token, safe_add
from app.notifications import push_notification

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
# View Wallet
# --------------------------
@router.get("/")
def view_wallet(current_user: User = Depends(get_current_user)):
    return {
        "wallet_balance": float(current_user.wallet_balance),
        "ledger_entries": [{"id": l.id, "type": l.type, "amount": float(l.amount), "created_at": l.created_at} for l in current_user.ledgers]
    }

# --------------------------
# Request Withdrawal
# --------------------------
@router.post("/withdraw")
def request_withdrawal(
    account_number: str,
    bank_code: str,
    amount: Decimal,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    MIN_WITHDRAWAL = Decimal("1000")
    WITHDRAWAL_FEE = Decimal("0.03")  # 3%

    if amount < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is {MIN_WITHDRAWAL} Naira")
    if current_user.wallet_balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    # Deduct fee
    fee = amount * WITHDRAWAL_FEE
    net_amount = amount - fee
    current_user.wallet_balance -= amount

    # Create withdrawal request (manual admin approval)
    withdrawal = Withdrawal(
        user_id=current_user.id,
        amount=net_amount,
        fee=fee,
        account_number=account_number,
        bank_code=bank_code,
        status="pending"
    )
    db.add(withdrawal)

    # Ledger entries (debit user, hold fee)
    ledger_entry = Ledger(
        user_id=current_user.id,
        amount=-amount,
        type="withdrawal_request",
        reference=f"withdrawal_{withdrawal.id}"
    )
    db.add(ledger_entry)

    db.add(current_user)
    db.commit()
    push_notification(current_user.id, f"Withdrawal request of {float(net_amount)} Naira submitted. Pending admin approval.")
    return {"status": "success", "net_amount": float(net_amount), "fee": float(fee), "message": "Withdrawal request submitted"}
