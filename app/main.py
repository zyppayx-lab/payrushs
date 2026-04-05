import logging
from datetime import datetime
from decimal import Decimal

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth, users, vendors, tasks, wallet, admin, notifications
from app.database import SessionLocal, engine, Base
from app.auto_tasks import scheduler, auto_approve_tasks, check_referral_bonus
from app.ai_agent import run_fraud_checks
from app.utils import push_notification
from app.config import ENVIRONMENT, FRONTEND_ORIGIN

# --------------------------
# Logging
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("dual-platform-backend")

# --------------------------
# Initialize DB
# --------------------------
Base.metadata.create_all(bind=engine)

# --------------------------
# FastAPI App
# --------------------------
app = FastAPI(
    title="Dual-Platform Tasks & Vendors",
    version="1.0",
    description="Production-ready backend for tasks earning + vendors platform"
)

# --------------------------
# CORS
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --------------------------
# Global Exception Handler
# --------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

# --------------------------
# Include Routers
# --------------------------
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# --------------------------
# Root & Health Check
# --------------------------
@app.get("/", tags=["Root"])
def root():
    return {"status": "Dual-Platform Backend Running"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "environment": ENVIRONMENT, "time": datetime.utcnow()}

# --------------------------
# Startup / Shutdown Events
# --------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Dual-Platform Backend...")
    scheduler.start()
    logger.info("Scheduler started.")
    logger.info("Backend fully initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Dual-Platform Backend...")
    scheduler.shutdown()
    logger.info("Scheduler stopped.")

# --------------------------
# Webhook Endpoint for Paystack Deposit Verification
# --------------------------
@app.post("/webhook/paystack")
async def paystack_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Handles Paystack deposit verification webhook
    Auto-credit wallet with fee deduction (0.75%), signup bonus (500 Naira), and referral bonus
    """
    event = payload.get("event")
    data = payload.get("data", {})

    if event != "charge.success":
        return {"status": "ignored"}

    reference = data.get("reference")
    amount_kobo = data.get("amount")  # Paystack amount in kobo
    customer = data.get("customer", {})
    user_email = customer.get("email")

    if not reference or not user_email:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    db = SessionLocal()
    try:
        from app.models import User, Ledger
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Convert kobo → Naira and apply 0.75% fee
        deposit_amount = Decimal(amount_kobo) / 100
        fee = (deposit_amount * Decimal("0.0075")).quantize(Decimal("0.01"))
        net_credit = (deposit_amount - fee).quantize(Decimal("0.01"))

        # Update user wallet
        user.wallet_balance += net_credit
        db.add(user)

        # Ledger entry
        ledger_entry = Ledger(
            user_id=user.id,
            amount=net_credit,
            type="deposit",
            reference=reference,
            created_at=datetime.utcnow()
        )
        db.add(ledger_entry)

        # Signup bonus
        if not user.has_received_signup_bonus:
            user.wallet_balance += Decimal("500.00")
            user.has_received_signup_bonus = True
            db.add(user)
            push_notification(user.id, "Signup bonus of 500 Naira credited!")

        # Referral bonus background task
        background_tasks.add_task(check_referral_bonus, user.id)

        db.commit()
        push_notification(user.id, f"Deposit of {net_credit} Naira credited to your wallet!")

    finally:
        db.close()

    return {"status": "success", "credited": float(net_credit)}

# --------------------------
# Background Scheduler Example
# --------------------------
@app.on_event("startup")
async def start_background_jobs():
    def scheduled_jobs():
        logger.info("Running scheduled auto-approval + fraud checks...")
        auto_approve_tasks()   # Auto-approve tasks older than 24h if vendor hasn't approved
        run_fraud_checks()     # Run AI fraud checks
    scheduler.add_job(scheduled_jobs, 'interval', minutes=10)  # every 10 mins
