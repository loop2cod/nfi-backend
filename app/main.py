from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.database import engine, Base
from app.routers.auth.auth_router import router as auth_router
from app.routers.dashboard.dashboard_router import router as dashboard_router
from app.routers.settings.settings_router import router as settings_router
from app.routers.webhook.sumsub_webhook import router as webhook_router
from app.routers.verification.verification_router import router as verification_router
from app.routers.wallets.wallets_router import router as wallets_router
from app.routers.admin.admin_router import router as admin_router
from app.routers.admin.admin_auth_router import router as admin_auth_router
from app.routers.admin.admin_management_router import router as admin_management_router
from app.routers.bvnk.bvnk_agreement_router import router as bvnk_agreement_router
from app.routers.bvnk.bvnk_customer_router import router as bvnk_customer_router
from app.routers.profile.profile_router import router as profile_router
from app.routers.totp.totp_router import router as totp_router
from app.core.dfns_client import init_dfns_client

# Import models to ensure they are registered with SQLAlchemy
# Import all models - SQLAlchemy will handle dependencies
import app.models.admin_login_history
import app.models.admin_user
import app.models.login_activity
import app.models.user
import app.models.user_counter
import app.models.verification_event
import app.models.wallet
import app.models.customer_verification_data

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize Dfns client
init_dfns_client()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="NFI Platform API",
    description="A comprehensive multi-tenant neo banking platform with 4-tier architecture",
    version="1.0.0"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
app.include_router(verification_router, prefix="/verification", tags=["verification"])
app.include_router(wallets_router, prefix="/wallets", tags=["wallets"])
app.include_router(admin_auth_router, prefix="/admin/auth", tags=["admin-auth"])
app.include_router(admin_management_router, prefix="/admin", tags=["admin-management"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(bvnk_agreement_router, prefix="/bvnk", tags=["bvnk-agreements"])
app.include_router(bvnk_customer_router, prefix="/bvnk", tags=["bvnk-customers"])
app.include_router(profile_router, tags=["profile"])
app.include_router(totp_router, tags=["totp"])

@app.get("/")
def read_root():
    return {"message": "Welcome to NFI Platform API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}