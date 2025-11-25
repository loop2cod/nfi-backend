from sqlalchemy import Column, Integer, String
from sqlalchemy.sql import func
from app.core.database import Base


class UserCounter(Base):
    """
    Tracks the counter for generating unique user IDs per month.
    Format: NF-MMYYYY### (e.g., NF-012025001, NF-012025002, ..., NF-012025999)
    """
    __tablename__ = "user_counters"

    id = Column(Integer, primary_key=True, index=True)
    month_year = Column(String, unique=True, nullable=False, index=True)  # Format: "MMYYYY" (e.g., "012025")
    counter = Column(Integer, default=0, nullable=False)  # Current counter value (0-999)

    @staticmethod
    def format_month_year(month: int, year: int) -> str:
        """Format month and year as MMYYYY"""
        return f"{month:02d}{year}"

    @staticmethod
    def format_user_id(month_year: str, counter: int) -> str:
        """Format user ID as NF-MMYYYY###"""
        return f"NF-{month_year}{counter:03d}"
