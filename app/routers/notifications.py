from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Notification, User
from app.utils import decode_access_token
from typing import List

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
# Fetch Notifications
# --------------------------
@router.get("/", response_model=List[dict])
def fetch_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "read": n.read,
            "created_at": n.created_at
        }
        for n in notifications
    ]

# --------------------------
# Mark Notification as Read
# --------------------------
@router.post("/{notification_id}/read")
def mark_as_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    db.add(notification)
    db.commit()
    return {"status": "success", "message": "Notification marked as read"}

# --------------------------
# Push Notification Utility (Optional)
# --------------------------
# Real-time push notifications would be handled via Redis queue (Upstash)
# The push_notification function from utils.py or notifications.py can be called
# whenever an event occurs (task approval, withdrawal, referral bonus, AI fraud alert)
