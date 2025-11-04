from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String, nullable=False)  # USDT, USDC, ETH, BTC
    address = Column(String, nullable=False, unique=True)
    balance = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)
    frozen_balance = Column(Float, default=0.0)
    network = Column(String, nullable=False)  # e.g., Ethereum, Bitcoin
    wallet_id = Column(String, nullable=False)  # Dfns wallet ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="wallets")