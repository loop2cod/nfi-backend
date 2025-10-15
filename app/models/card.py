from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum

class CardType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    VIRTUAL = "virtual"

class CardStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class CardBase(BaseModel):
    account_id: str
    card_type: CardType
    card_name: Optional[str] = Field(None, max_length=50)

class CardCreate(CardBase):
    pass

class Card(CardBase):
    id: str
    card_number: str  # Should be masked in real responses
    cvv: str  # Should never be returned in API responses
    expiry_date: date
    status: CardStatus = CardStatus.ACTIVE
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CardResponse(BaseModel):
    id: str
    card_number_masked: str  # e.g., "**** **** **** 1234"
    card_type: CardType
    card_name: Optional[str]
    expiry_date: date
    status: CardStatus
    created_at: datetime

    class Config:
        from_attributes = True
