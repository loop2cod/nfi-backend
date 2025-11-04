from fastapi import APIRouter, Depends
from app.routers.auth.auth_router import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/stat", response_model=dict)
def get_dashboard(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Welcome to your dashboard, {current_user.email}!",
        "user_id": current_user.id,
        "features": [
            "Virtual accounts",
            "Accept payments",
            "Send payments",
            "Instant transfers"
        ]
    }