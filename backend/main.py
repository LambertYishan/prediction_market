"""FastAPI application exposing a minimal prediction market API.

This module wires together the database models, market logic and API
endpoints described in the project outline. It supports basic user
registration and login, market creation and listing, placing bets using an
LMSR automated market maker and resolving markets. The API uses JSON for
all input and output. Authentication is deliberately simple to keep the
starter template approachable; in a real application, one would use JWTs or
similar tokens instead of returning the user ID directly.
"""

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import User, Market, Bet
from backend.market_logic import cost_for_shares, price_yes, price_no

import hashlib


# Create database tables. In production you may want to manage migrations
# separately using Alembic, but for a quick start this is convenient.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prediction Market API", version="0.1.0")

# Allow all origins by default to facilitate local development and
# deployment of the frontend on a different host (e.g. GitHub Pages). In a
# production environment you should restrict this to the domains serving
# your frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_password_hash(password: str) -> str:
    """Compute a SHA‑256 hash of the given password.

    A proper application should use a stronger hashing algorithm like bcrypt
    with a salt. This simplified example uses SHA‑256 for brevity and ease of
    installation. The resulting hex digest is stored in the database.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its SHA‑256 hash."""
    return get_password_hash(plain_password) == hashed_password


# Pydantic models for request and response bodies. These enforce input
# validation and generate API documentation automatically.

class RegisterRequest(BaseModel):
    username: str = Field(..., example="alice")
    password: str = Field(..., min_length=3, example="secret123")


class LoginRequest(BaseModel):
    username: str = Field(..., example="alice")
    password: str = Field(..., example="secret123")


class MarketCreateRequest(BaseModel):
    title: str = Field(..., example="Will it rain tomorrow?")
    description: Optional[str] = Field(None, example="Weather forecast for New York City.")
    liquidity: Optional[float] = Field(None, example=100.0)


class BetRequest(BaseModel):
    user_id: int = Field(..., example=1)
    market_id: int = Field(..., example=1)
    side: str = Field(..., pattern="^(YES|NO|yes|no)$", example="YES")
    amount: float = Field(..., gt=0.0, example=5.0)


class ResolveRequest(BaseModel):
    market_id: int = Field(..., example=1)
    outcome: str = Field(..., regex="^(YES|NO|yes|no)$", example="YES")


class UserResponse(BaseModel):
    id: int
    username: str
    balance: float
    class Config:
        orm_mode = True


class MarketResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    yes_shares: float
    no_shares: float
    liquidity: float
    resolved: bool
    outcome: Optional[str]
    price_yes: float
    price_no: float
    class Config:
        orm_mode = True


class BetResponse(BaseModel):
    id: int
    user_id: int
    market_id: int
    side: str
    amount: float
    price: float
    total_cost: float
    timestamp: str
    class Config:
        orm_mode = True


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user with the provided username and password.

    The password is hashed before storing. Usernames must be unique.
    Returns the newly created user's ID, username and balance.
    """
    # Check if the username is already taken
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(
        username=request.username,
        password_hash=get_password_hash(request.password),
        balance=100.0
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user by username and password.

    On success returns a simple dict containing the user's ID and balance.
    In a production application you'd return a session or JWT token instead.
    """
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {"id": user.id, "username": user.username, "balance": user.balance}


@app.get("/markets", response_model=List[MarketResponse])
def list_markets(db: Session = Depends(get_db)):
    """Return all markets with current prices.

    Prices are computed on the fly using the LMSR cost function. For each
    market the YES and NO probabilities are added to the response.
    """
    markets = db.query(Market).all()
    response = []
    for m in markets:
        b = m.liquidity
        # If the market is resolved, the price is simply 1 for the winning
        # outcome and 0 for the losing one.
        if m.resolved and m.outcome in {"YES", "NO"}:
            p_yes = 1.0 if m.outcome == "YES" else 0.0
            p_no = 1.0 - p_yes
        else:
            p_yes = price_yes(m.yes_shares, m.no_shares, b)
            p_no = 1.0 - p_yes
        response.append(MarketResponse(
            id=m.id,
            title=m.title,
            description=m.description,
            yes_shares=m.yes_shares,
            no_shares=m.no_shares,
            liquidity=m.liquidity,
            resolved=m.resolved,
            outcome=m.outcome,
            price_yes=p_yes,
            price_no=p_no
        ))
    return response


@app.post("/markets", response_model=MarketResponse, status_code=status.HTTP_201_CREATED)
def create_market(request: MarketCreateRequest, db: Session = Depends(get_db)):
    """Create a new market. Only an admin should call this in practice.

    Accepts a title, optional description and optional liquidity parameter.
    Returns the full market details including computed initial prices.
    """
    liquidity = request.liquidity if request.liquidity and request.liquidity > 0 else 100.0
    market = Market(
        title=request.title,
        description=request.description,
        liquidity=liquidity,
        yes_shares=0.0,
        no_shares=0.0,
        resolved=False,
        outcome=None
    )
    db.add(market)
    db.commit()
    db.refresh(market)
    # Compute initial prices (both 0.5 for a balanced LMSR)
    p_yes = 0.5
    p_no = 0.5
    return MarketResponse(
        id=market.id,
        title=market.title,
        description=market.description,
        yes_shares=market.yes_shares,
        no_shares=market.no_shares,
        liquidity=market.liquidity,
        resolved=market.resolved,
        outcome=market.outcome,
        price_yes=p_yes,
        price_no=p_no
    )


@app.post("/bet", response_model=BetResponse)
def place_bet(request: BetRequest, db: Session = Depends(get_db)):
    """Place a bet on a market.

    The cost of the bet is calculated via the LMSR cost function. The user's
    balance is reduced by the total cost and the market's YES or NO shares
    are updated by the amount purchased. A new ``Bet`` record is created.

    Returns:
        BetResponse: details of the recorded bet including price per share
        and total cost. If the user has insufficient funds or the market is
        resolved, an error is raised.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    market = db.query(Market).filter(Market.id == request.market_id).first()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    if market.resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Market is already resolved")

    side_upper = request.side.upper()
    # Compute cost using current share counts and liquidity parameter
    total_cost = cost_for_shares(market.yes_shares, market.no_shares, request.amount, side_upper, market.liquidity)

    # Ensure the user can afford the bet
    if user.balance < total_cost:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance to place bet")

    # Update the market's share totals
    if side_upper == "YES":
        market.yes_shares += request.amount
    else:
        market.no_shares += request.amount

    # Deduct cost from user's balance
    user.balance -= total_cost

    # Calculate price per share
    price_per_share = total_cost / request.amount

    # Create Bet record
    bet = Bet(
        user_id=user.id,
        market_id=market.id,
        side=side_upper,
        amount=request.amount,
        price=price_per_share,
        total_cost=total_cost
    )
    db.add(bet)
    db.commit()
    db.refresh(bet)
    return BetResponse(
        id=bet.id,
        user_id=bet.user_id,
        market_id=bet.market_id,
        side=bet.side,
        amount=bet.amount,
        price=bet.price,
        total_cost=bet.total_cost,
        timestamp=bet.timestamp.isoformat()
    )


@app.post("/resolve", response_model=MarketResponse)
def resolve_market(request: ResolveRequest, db: Session = Depends(get_db)):
    """Resolve a market to a final outcome ('YES' or 'NO').

    Once resolved, the market's outcome is fixed and prices become 1 for the
    winning side and 0 for the losing side. All outstanding shares of the
    winning outcome are redeemed at value 1 and credited back to users. This
    simplistic implementation iterates over all bets and credits balances
    accordingly.
    """
    market = db.query(Market).filter(Market.id == request.market_id).first()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    if market.resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Market has already been resolved")
    outcome_upper = request.outcome.upper()
    if outcome_upper not in {"YES", "NO"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outcome must be 'YES' or 'NO'")

    # Mark market as resolved
    market.resolved = True
    market.outcome = outcome_upper

    # Payout winners: iterate through all bets on this market
    bets = db.query(Bet).filter(Bet.market_id == market.id).all()
    for bet in bets:
        # If the bet matches the outcome, credit the user the number of shares
        if bet.side == outcome_upper:
            user = db.query(User).filter(User.id == bet.user_id).first()
            # Credit 1 currency unit per share; total = amount
            user.balance += bet.amount
    db.commit()

    # Recompute prices: set to 1 for winning outcome and 0 for losing
    p_yes = 1.0 if outcome_upper == "YES" else 0.0
    p_no = 1.0 - p_yes
    return MarketResponse(
        id=market.id,
        title=market.title,
        description=market.description,
        yes_shares=market.yes_shares,
        no_shares=market.no_shares,
        liquidity=market.liquidity,
        resolved=market.resolved,
        outcome=market.outcome,
        price_yes=p_yes,
        price_no=p_no
    )


@app.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return information about a single user.

    Includes the current balance. Bets are not returned here to keep the
    response simple; they can be fetched via separate endpoints if needed.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=user.id, username=user.username, balance=user.balance)


@app.get("/")
def root():
    return {"message": "Prediction Market API is running!"}
