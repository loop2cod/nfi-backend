from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.transaction import TransactionCreate, TransactionResponse, Transaction
from decimal import Decimal
import uuid
from datetime import datetime
import random

router = APIRouter()

# Mock database
transactions_db = {}

def generate_reference_number() -> str:
    """Generate a unique reference number for transactions."""
    return f"TXN{datetime.now().strftime('%Y%m%d')}{random.randint(100000, 999999)}"

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, summary="Create a new transaction")
async def create_transaction(transaction: TransactionCreate):
    """
    Create a new transaction:
    - **from_account_id**: Source account ID
    - **to_account_id**: Destination account ID (optional for deposits/withdrawals)
    - **amount**: Transaction amount (must be positive)
    - **transaction_type**: Type (deposit, withdrawal, transfer, payment)
    - **description**: Optional description
    """
    # Validate transaction type requirements
    if transaction.transaction_type == "transfer" and not transaction.to_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer transactions require a destination account"
        )

    transaction_id = str(uuid.uuid4())
    reference_number = generate_reference_number()

    new_transaction = {
        "id": transaction_id,
        "from_account_id": transaction.from_account_id,
        "to_account_id": transaction.to_account_id,
        "amount": transaction.amount,
        "transaction_type": transaction.transaction_type,
        "description": transaction.description,
        "status": "completed",  # In real app, would start as pending
        "reference_number": reference_number,
        "created_at": datetime.now(),
    }

    transactions_db[transaction_id] = new_transaction
    return TransactionResponse(**new_transaction)

@router.get("/", response_model=List[TransactionResponse], summary="Get all transactions")
async def get_transactions(account_id: str = None, limit: int = 100):
    """
    Retrieve transactions, optionally filtered by account_id.
    - **account_id**: Filter by account (returns both sent and received)
    - **limit**: Maximum number of transactions to return (default: 100)
    """
    transactions = list(transactions_db.values())

    if account_id:
        transactions = [
            txn for txn in transactions
            if txn["from_account_id"] == account_id or txn["to_account_id"] == account_id
        ]

    # Sort by creation date (newest first)
    transactions.sort(key=lambda x: x["created_at"], reverse=True)

    return [TransactionResponse(**txn) for txn in transactions[:limit]]

@router.get("/{transaction_id}", response_model=TransactionResponse, summary="Get transaction by ID")
async def get_transaction(transaction_id: str):
    """
    Retrieve a specific transaction by its ID.
    """
    if transaction_id not in transactions_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return TransactionResponse(**transactions_db[transaction_id])

@router.get("/reference/{reference_number}", response_model=TransactionResponse, summary="Get transaction by reference number")
async def get_transaction_by_reference(reference_number: str):
    """
    Retrieve a transaction by its reference number.
    """
    for transaction in transactions_db.values():
        if transaction["reference_number"] == reference_number:
            return TransactionResponse(**transaction)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Transaction not found"
    )

@router.patch("/{transaction_id}/cancel", response_model=TransactionResponse, summary="Cancel a transaction")
async def cancel_transaction(transaction_id: str):
    """
    Cancel a pending transaction.
    """
    if transaction_id not in transactions_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    transaction = transactions_db[transaction_id]

    if transaction["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed transaction"
        )

    transactions_db[transaction_id]["status"] = "cancelled"
    return TransactionResponse(**transactions_db[transaction_id])
