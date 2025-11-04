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
from app.core.dfns_client import init_dfns_client

# Import models to ensure they are registered with SQLAlchemy
import app.models.user
import app.models.verification_event
import app.models.wallet

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

@app.get("/")
def read_root():
    return {"message": "Welcome to NFI Platform API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}