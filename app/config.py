import os

# --------------------------
# Environment
# --------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")  # production / development
DEBUG = ENVIRONMENT != "production"

# --------------------------
# Frontend
# --------------------------
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")  # replace * with your frontend URL in production

# --------------------------
# Paystack
# --------------------------
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")

# --------------------------
# Upstash Redis
# --------------------------
UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")

# --------------------------
# JWT & Fernet
# --------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")
FERNET_KEY = os.getenv("FERNET_KEY")  # must be a 32-byte base64 key

# --------------------------
# Scheduler settings
# --------------------------
TASK_AUTO_APPROVE_HOURS = int(os.getenv("TASK_AUTO_APPROVE_HOURS", 24))
REFERRAL_BONUS_TASK_COUNT = int(os.getenv("REFERRAL_BONUS_TASK_COUNT", 2))
SIGNUP_BONUS = float(os.getenv("SIGNUP_BONUS", 500))
REFERRAL_BONUS = float(os.getenv("REFERRAL_BONUS", 200))

# --------------------------
# Wallet Fees
# --------------------------
DEPOSIT_FEE_PERCENT = float(os.getenv("DEPOSIT_FEE_PERCENT", 0.75))
WITHDRAWAL_FEE_PERCENT = float(os.getenv("WITHDRAWAL_FEE_PERCENT", 3))
MIN_WITHDRAWAL_AMOUNT = float(os.getenv("MIN_WITHDRAWAL_AMOUNT", 1000))
