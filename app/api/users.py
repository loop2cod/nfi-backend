from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.user import UserCreate, UserResponse, User

router = APIRouter()

# Mock database (replace with actual database in production)
users_db = {}

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user")
async def create_user(user: UserCreate):
    """
    Create a new user account with the following information:
    - **email**: Valid email address
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **phone**: Phone number in international format
    - **password**: Minimum 8 characters
    """
    # Check if user already exists
    for existing_user in users_db.values():
        if existing_user["email"] == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    from datetime import datetime
    import uuid

    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "status": "active",
        "created_at": datetime.now(),
    }

    users_db[user_id] = new_user
    return UserResponse(**new_user)

@router.get("/", response_model=List[UserResponse], summary="Get all users")
async def get_users():
    """
    Retrieve a list of all registered users.
    """
    return [UserResponse(**user) for user in users_db.values()]

@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(user_id: str):
    """
    Retrieve a specific user by their ID.
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse(**users_db[user_id])

@router.put("/{user_id}", response_model=UserResponse, summary="Update user")
async def update_user(user_id: str, user: UserCreate):
    """
    Update an existing user's information.
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    users_db[user_id].update({
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
    })

    return UserResponse(**users_db[user_id])

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
async def delete_user(user_id: str):
    """
    Delete a user account.
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    del users_db[user_id]
    return None
