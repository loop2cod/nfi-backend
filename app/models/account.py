from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal

class AccountType(str, Enum):
    SAVINGS = "savings"
    CHECKING = "checking"
    BUSINESS = "business"

class AccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"

class AccountBase(BaseModel):
    user_id: str
    account_type: AccountType
    currency: Currency = Currency.USD

class AccountCreate(AccountBase):
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)

class Account(AccountBase):
    id: str
    account_number: str
    balance: Decimal
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AccountResponse(BaseModel):
    id: str
    account_number: str
    account_type: AccountType
    balance: Decimal
    currency: Currency
    status: AccountStatus
    created_at: datetime

    class Config:
        from_attributes = True
