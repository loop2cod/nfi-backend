"""
User ID Generation Service
Generates unique user IDs in the format: NF-MMYYYY### (e.g., NF-012025001)
- MM: Month (01-12)
- YYYY: Year (e.g., 2025)
- ###: Sequential counter (001-999) that resets each month
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user_counter import UserCounter


def generate_user_id(db: Session) -> str:
    """
    Generate a unique user ID for the current month.
    Format: NF-MMYYYY### (e.g., NF-012025001, NF-012025002, ..., NF-012025999)

    Args:
        db: Database session

    Returns:
        str: Generated user ID

    Raises:
        ValueError: If monthly limit (999) is reached
    """
    now = datetime.utcnow()
    month = now.month
    year = now.year
    month_year = UserCounter.format_month_year(month, year)

    # Get or create counter for this month
    counter_record = db.query(UserCounter).filter(
        UserCounter.month_year == month_year
    ).with_for_update().first()

    if counter_record is None:
        # Create new counter for this month
        counter_record = UserCounter(
            month_year=month_year,
            counter=1
        )
        db.add(counter_record)
        db.flush()  # Flush to get the counter value
        user_id = UserCounter.format_user_id(month_year, counter_record.counter)
    else:
        # Increment existing counter
        if counter_record.counter >= 999:
            raise ValueError(f"Monthly user ID limit reached for {month_year}. Maximum 999 users per month.")

        counter_record.counter += 1
        db.flush()  # Flush to update the counter
        user_id = UserCounter.format_user_id(month_year, counter_record.counter)

    return user_id


def get_current_month_stats(db: Session) -> dict:
    """
    Get statistics for the current month's user registrations.

    Args:
        db: Database session

    Returns:
        dict: Statistics including current counter, remaining slots, and month_year
    """
    now = datetime.utcnow()
    month = now.month
    year = now.year
    month_year = UserCounter.format_month_year(month, year)

    counter_record = db.query(UserCounter).filter(
        UserCounter.month_year == month_year
    ).first()

    if counter_record is None:
        return {
            "month_year": month_year,
            "current_count": 0,
            "remaining": 999,
            "limit": 999,
            "is_full": False
        }

    return {
        "month_year": month_year,
        "current_count": counter_record.counter,
        "remaining": 999 - counter_record.counter,
        "limit": 999,
        "is_full": counter_record.counter >= 999
    }
