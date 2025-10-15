from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.account import AccountCreate, AccountResponse, Account
from decimal import Decimal
import uuid
from datetime import datetime
import random

router = APIRouter()

# Mock database
accounts_db = {}

def generate_account_number() -> str:
    """Generate a random account number."""
    return "".join([str(random.randint(0, 9)) for _ in range(12)])

@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED, summary="Create a new account")
async def create_account(account: AccountCreate):
    """
    Create a new bank account for a user:
    - **user_id**: ID of the user creating the account
    - **account_type**: Type of account (savings, checking, business)
    - **currency**: Account currency (default: USD)
    - **initial_balance**: Starting balance (default: 0.00)
    """
    account_id = str(uuid.uuid4())
    account_number = generate_account_number()

    new_account = {
        "id": account_id,
        "user_id": account.user_id,
        "account_number": account_number,
        "account_type": account.account_type,
        "currency": account.currency,
        "balance": account.initial_balance,
        "status": "active",
        "created_at": datetime.now(),
    }

    accounts_db[account_id] = new_account
    return AccountResponse(**new_account)

@router.get("/", response_model=List[AccountResponse], summary="Get all accounts")
async def get_accounts(user_id: str = None):
    """
    Retrieve all accounts, optionally filtered by user_id.
    """
    if user_id:
        filtered = [acc for acc in accounts_db.values() if acc["user_id"] == user_id]
        return [AccountResponse(**acc) for acc in filtered]

    return [AccountResponse(**acc) for acc in accounts_db.values()]

@router.get("/{account_id}", response_model=AccountResponse, summary="Get account by ID")
async def get_account(account_id: str):
    """
    Retrieve a specific account by its ID.
    """
    if account_id not in accounts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return AccountResponse(**accounts_db[account_id])

@router.get("/{account_id}/balance", summary="Get account balance")
async def get_balance(account_id: str):
    """
    Get the current balance of an account.
    """
    if account_id not in accounts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    account = accounts_db[account_id]
    return {
        "account_id": account_id,
        "account_number": account["account_number"],
        "balance": account["balance"],
        "currency": account["currency"]
    }

@router.patch("/{account_id}/freeze", response_model=AccountResponse, summary="Freeze account")
async def freeze_account(account_id: str):
    """
    Freeze an account to prevent transactions.
    """
    if account_id not in accounts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    accounts_db[account_id]["status"] = "frozen"
    return AccountResponse(**accounts_db[account_id])

@router.patch("/{account_id}/activate", response_model=AccountResponse, summary="Activate account")
async def activate_account(account_id: str):
    """
    Activate a frozen account.
    """
    if account_id not in accounts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    accounts_db[account_id]["status"] = "active"
    return AccountResponse(**accounts_db[account_id])

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Close account")
async def close_account(account_id: str):
    """
    Close an account (soft delete by marking as closed).
    """
    if account_id not in accounts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    accounts_db[account_id]["status"] = "closed"
    return None
