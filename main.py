from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import users, accounts, transactions, cards, rbac
from app.api import auth_v2 as auth
from app.core.config import settings

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    from app.db.connection import get_db, close_db
    print("🚀 Starting NFI Platform API...")

    # Initialize database connection
    get_db()
    print("📊 Database: Connected")

    yield

    # Shutdown
    close_db()
    print("👋 NFI Platform API shutting down...")

app = FastAPI(
    title="NFI Platform API",
    description="""
    # Multi-Tenant Neo Banking Platform

    A comprehensive 4-tier digital banking infrastructure supporting:

    ## Architecture Tiers
    1. **Platform (Tier 0)**: Super Admin Dashboard - Platform management
    2. **Client (Tier 1)**: Company/Bank Dashboard - Client administration
    3. **SubClient (Tier 2)**: Financial Institution Dashboard - Operations
    4. **End User (Tier 3)**: Customer Portal - Individual banking

    ## Core Features
    - Multi-tenant user management with hierarchical access control
    - Role-based permissions (RBAC) across 11 user roles
    - JWT authentication with refresh tokens
    - KYC verification (Sumsub & Onfido integration ready)
    - Digital wallets and account management
    - Transaction processing and monitoring
    - Card issuance and management

    ## Security
    - OAuth2 with JWT tokens
    - Password hashing with bcrypt
    - Role-based access control (RBAC)
    - Multi-factor authentication ready
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "NFI Platform Support",
        "email": "support@nfigate.com",
    },
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication & Authorization
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(rbac.router, prefix="/api/v1/rbac", tags=["RBAC & Permissions"])

# Core Resources
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["Accounts"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(cards.router, prefix="/api/v1/cards", tags=["Cards"])

@app.get("/", summary="Root endpoint", response_description="Welcome message")
async def root():
    """
    Root endpoint that provides basic API information and documentation links.
    """
    return {
        "message": "Welcome to NFI Platform API",
        "platform": "Multi-Tenant Neo Banking System",
        "version": "1.0.0",
        "architecture": "4-Tier (Platform → Client → SubClient → End User)",
        "docs": "/docs",
        "redoc": "/redoc",
        "authentication": "/api/v1/auth/login",
        "rbac": "/api/v1/rbac/hierarchy"
    }

@app.get("/health", summary="Health check", response_description="Health status")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    from app.db.connection import get_db

    # Check  connection
    try:
        db = get_db()
        db.fetch_value("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0"
    }

