from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.card import CardCreate, CardResponse, Card
import uuid
from datetime import datetime, date, timedelta
import random

router = APIRouter()

# Mock database
cards_db = {}

def generate_card_number() -> str:
    """Generate a random 16-digit card number."""
    return "".join([str(random.randint(0, 9)) for _ in range(16)])

def generate_cvv() -> str:
    """Generate a random 3-digit CVV."""
    return "".join([str(random.randint(0, 9)) for _ in range(3)])

def mask_card_number(card_number: str) -> str:
    """Mask card number showing only last 4 digits."""
    return f"**** **** **** {card_number[-4:]}"

@router.post("/", response_model=CardResponse, status_code=status.HTTP_201_CREATED, summary="Issue a new card")
async def create_card(card: CardCreate):
    """
    Issue a new card for an account:
    - **account_id**: ID of the account to link the card to
    - **card_type**: Type of card (debit, credit, virtual)
    - **card_name**: Optional custom name for the card
    """
    card_id = str(uuid.uuid4())
    card_number = generate_card_number()
    cvv = generate_cvv()
    expiry_date = date.today() + timedelta(days=365*3)  # 3 years validity

    new_card = {
        "id": card_id,
        "account_id": card.account_id,
        "card_number": card_number,
        "cvv": cvv,
        "card_type": card.card_type,
        "card_name": card.card_name,
        "expiry_date": expiry_date,
        "status": "active",
        "created_at": datetime.now(),
    }

    cards_db[card_id] = new_card

    # Return masked card number
    return CardResponse(
        id=card_id,
        card_number_masked=mask_card_number(card_number),
        card_type=card.card_type,
        card_name=card.card_name,
        expiry_date=expiry_date,
        status="active",
        created_at=new_card["created_at"]
    )

@router.get("/", response_model=List[CardResponse], summary="Get all cards")
async def get_cards(account_id: str = None):
    """
    Retrieve all cards, optionally filtered by account_id.
    """
    cards = list(cards_db.values())

    if account_id:
        cards = [card for card in cards if card["account_id"] == account_id]

    return [
        CardResponse(
            id=card["id"],
            card_number_masked=mask_card_number(card["card_number"]),
            card_type=card["card_type"],
            card_name=card["card_name"],
            expiry_date=card["expiry_date"],
            status=card["status"],
            created_at=card["created_at"]
        )
        for card in cards
    ]

@router.get("/{card_id}", response_model=CardResponse, summary="Get card by ID")
async def get_card(card_id: str):
    """
    Retrieve a specific card by its ID.
    """
    if card_id not in cards_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )

    card = cards_db[card_id]
    return CardResponse(
        id=card["id"],
        card_number_masked=mask_card_number(card["card_number"]),
        card_type=card["card_type"],
        card_name=card["card_name"],
        expiry_date=card["expiry_date"],
        status=card["status"],
        created_at=card["created_at"]
    )

@router.patch("/{card_id}/block", response_model=CardResponse, summary="Block a card")
async def block_card(card_id: str):
    """
    Block a card to prevent unauthorized use.
    """
    if card_id not in cards_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )

    cards_db[card_id]["status"] = "blocked"
    card = cards_db[card_id]

    return CardResponse(
        id=card["id"],
        card_number_masked=mask_card_number(card["card_number"]),
        card_type=card["card_type"],
        card_name=card["card_name"],
        expiry_date=card["expiry_date"],
        status=card["status"],
        created_at=card["created_at"]
    )

@router.patch("/{card_id}/unblock", response_model=CardResponse, summary="Unblock a card")
async def unblock_card(card_id: str):
    """
    Unblock a previously blocked card.
    """
    if card_id not in cards_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )

    cards_db[card_id]["status"] = "active"
    card = cards_db[card_id]

    return CardResponse(
        id=card["id"],
        card_number_masked=mask_card_number(card["card_number"]),
        card_type=card["card_type"],
        card_name=card["card_name"],
        expiry_date=card["expiry_date"],
        status=card["status"],
        created_at=card["created_at"]
    )

@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cancel a card")
async def cancel_card(card_id: str):
    """
    Cancel a card permanently.
    """
    if card_id not in cards_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )

    cards_db[card_id]["status"] = "cancelled"
    return None
