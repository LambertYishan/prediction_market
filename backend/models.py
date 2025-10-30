"""Database models for the prediction market.

This module defines three core SQLAlchemy ORM models: ``User``, ``Market``
and ``Bet``. These models reflect the schema described in the project
outline. Relationships are added to simplify joining users with their bets
and markets with their bets.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from backend.database import Base


class User(Base):
    """Represents a registered user of the prediction market.

    Users have a unique username, a hashed password and a floating point
    balance. The default balance can be set when creating a new user in
    application logic; here we simply define the column with a default of
    100.0. A relationship is provided to access the user's bets.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    balance = Column(Float, default=100.0, nullable=False)
    last_bonus_claim = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    bets = relationship("Bet", back_populates="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Market(Base):
    """Represents a binary prediction market.

    Each market tracks the amount of YES and NO shares outstanding along with
    a liquidity parameter ``b`` used in the LMSR cost function. Markets may
    be unresolved or resolved to a particular outcome. Expiration and creation
    timestamps are included for filtering and tracking.
    """

    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    yes_shares = Column(Float, default=0.0, nullable=False)
    no_shares = Column(Float, default=0.0, nullable=False)
    liquidity = Column(Float, default=100.0, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    outcome = Column(String, nullable=True)  # 'YES', 'NO' or None

    # 🆕 Added timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)

    bets = relationship("Bet", back_populates="market")
    price_history = relationship("PriceHistory", backref="market")


class Bet(Base):
    """Records a single bet placed by a user on a market.

    Bets record the number of shares purchased, the side ('YES' or 'NO'),
    the total cost paid and the price per share at the time of purchase. A
    timestamp is automatically generated when the bet is inserted. Each bet
    references both a user and a market via foreign keys.
    """

    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    side = Column(String, nullable=False)  # 'YES' or 'NO'
    amount = Column(Float, nullable=False)  # Number of shares purchased
    price = Column(Float, nullable=False)   # Price per share at purchase
    total_cost = Column(Float, nullable=False)  # Total cost of the bet
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="bets")
    market = relationship("Market", back_populates="bets")


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = {'extend_existing': True} 
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    price_yes = Column(Float)
    price_no = Column(Float)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=True) 
    type = Column(String, nullable=False)  # e.g. 'BET', 'PAYOUT', 'BONUS', 'REFUND'
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)