from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TransactionBase(BaseModel):
    from_account_id: str
    to_account_id: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    transaction_type: TransactionType
    description: Optional[str] = Field(None, max_length=200)

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: str
    status: TransactionStatus = TransactionStatus.PENDING
    reference_number: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: str
    from_account_id: str
    to_account_id: Optional[str]
    amount: Decimal
    transaction_type: TransactionType
    status: TransactionStatus
    reference_number: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
