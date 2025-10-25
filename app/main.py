from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.routers.auth.auth_router import router as auth_router
from app.routers.dashboard.dashboard_router import router as dashboard_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NFI Platform API",
    description="A comprehensive multi-tenant neo banking platform with 4-tier architecture",
    version="1.0.0"
)

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

@app.get("/")
def read_root():
    return {"message": "Welcome to NFI Platform API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}