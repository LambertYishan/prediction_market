"""FastAPI application exposing a minimal prediction market API.

This module wires together the database models, market logic and API
endpoints described in the project outline. It supports basic user
registration and login, market creation and listing, placing bets using an
LMSR automated market maker and resolving markets. The API uses JSON for
all input and output. Authentication is deliberately simple to keep the
starter template approachable; in a real application, one would use JWTs or
similar tokens instead of returning the user ID directly.
"""

import os, tempfile, pathlib, contextlib

temp_db_path = os.path.join(tempfile.gettempdir(), "prediction_market.db")

# 🔥 Nuke any stale DB file from prior boot
with contextlib.suppress(FileNotFoundError):
    os.remove(temp_db_path)


from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from collections import defaultdict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect, text
import os
import pathlib


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import tempfile


from backend.database import Base, engine, get_db
from backend.models import User, Market, Bet, PriceHistory
from backend.market_logic import cost_for_shares, price_yes, price_no

import hashlib

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "lambert")  # fallback if .env missing
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "predictit123")


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
    allow_origins=[
        "https://lambertyishan.github.io",
        "https://lambertyishan.github.io/prediction_market"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Ensure all HTTPException responses include CORS headers.
    This prevents the browser from masking 4xx/5xx JSON errors as 'Network errors'.
    """
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    origin = request.headers.get("origin")
    if origin in [
        "https://lambertyishan.github.io",
        "https://lambertyishan.github.io/prediction_market"
    ]:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


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

def verify_admin(username: str, password: str):
    """Check if provided credentials match the single admin account."""
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )



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
    expires_at: Optional[datetime] = Field(None, example="2025-12-31T23:59:00Z")
    admin_username: str
    admin_password: str
    

class BetRequest(BaseModel):
    user_id: int = Field(..., example=1)
    market_id: int = Field(..., example=1)
    side: str = Field(..., pattern="^(YES|NO|yes|no)$", example="YES")
    amount: float = Field(..., gt=0.0, example=5.0)


class ResolveRequest(BaseModel):
    market_id: int = Field(..., example=1)
    outcome: str = Field(..., pattern="^(YES|NO|yes|no)$", example="YES")


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
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
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
    """Return all markets with current prices and status labels."""
    now = datetime.utcnow()
    markets = db.query(Market).all()

    response = []
    for m in markets:
        b = m.liquidity
        if m.resolved:
            p_yes = 1.0 if m.outcome == "YES" else 0.0
            p_no = 1.0 - p_yes
            status = "resolved"
        elif m.expires_at and m.expires_at < now:
            p_yes = price_yes(m.yes_shares, m.no_shares, b)
            p_no = 1.0 - p_yes
            status = "expired"
        else:
            p_yes = price_yes(m.yes_shares, m.no_shares, b)
            p_no = 1.0 - p_yes
            status = "active"

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
            price_no=p_no,
            created_at=m.created_at,
            expires_at=m.expires_at
        ).dict() | {"status": status})  # add dynamic status field
    return response



@app.post("/markets", response_model=MarketResponse, status_code=status.HTTP_201_CREATED)
def create_market(request: MarketCreateRequest, db: Session = Depends(get_db)):
    """Create a new market. Only an admin can create or modify markets."""
    verify_admin(request.admin_username, request.admin_password)

    liquidity = request.liquidity if request.liquidity and request.liquidity > 0 else 100.0
    expires_at = request.expires_at or datetime.now(timezone.utc) + timedelta(days=1)

    market = Market(
        title=request.title,
        description=request.description,
        liquidity=liquidity,
        yes_shares=0.0,
        no_shares=0.0,
        resolved=False,
        outcome=None,
        expires_at=expires_at
    )
    db.add(market)
    db.commit()
    db.refresh(market)
    return MarketResponse(
        id=market.id,
        title=market.title,
        description=market.description,
        yes_shares=market.yes_shares,
        no_shares=market.no_shares,
        liquidity=market.liquidity,
        resolved=market.resolved,
        outcome=market.outcome,
        price_yes=0.5,
        price_no=0.5
    )

@app.delete("/markets/{market_id}")
def delete_market(market_id: int, username: str, password: str, db: Session = Depends(get_db)):
    """Allow the admin to delete a market entirely."""
    verify_admin(username, password)
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    db.delete(market)
    db.commit()
    return {"detail": f"Market {market_id} deleted successfully"}



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

    # compute new prices
    p_yes = price_yes(market.yes_shares, market.no_shares, market.liquidity)
    p_no = 1 - p_yes

    # record snapshot
    price_entry = PriceHistory(
        market_id=market.id,
        price_yes=p_yes,
        price_no=p_no
    )
    db.add(price_entry)
    db.commit()

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
    """
    Resolve a market and credit winning shareholders atomically.

    - Admins may resolve early if needed (e.g. clear outcome known before expiry).
    - Markets that have passed their expiry date but remain unresolved can also be resolved.
    - The function sets outcome + credits winners + records whether resolution was early or post-expiry.
    """
    market = db.query(Market).filter(Market.id == request.market_id).with_for_update(nowait=False).first()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")

    if market.resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Market has already been resolved")

    outcome_upper = request.outcome.upper()
    if outcome_upper not in {"YES", "NO"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outcome must be 'YES' or 'NO'")

    # Detect timing of resolution
    now = datetime.now(timezone.utc)
    # normalize market.expires_at for comparison
    expires_at = market.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at:
        if now < expires_at:
            resolution_note = "Resolved early by admin (before expiry)."
        else:
            resolution_note = "Resolved after natural expiry."
    else:
        resolution_note = "Resolved by admin (no expiry date set)."

    try:
        # 1️⃣ Collect all bets
        bets = db.query(Bet).filter(Bet.market_id == market.id).all()
        credit_by_user = defaultdict(float)
        for bet in bets:
            if bet.side and bet.side.upper() == outcome_upper:
                credit_by_user[bet.user_id] += bet.amount  # Each winning share = $1

        # 2️⃣ Apply credits
        if credit_by_user:
            users = db.query(User).filter(User.id.in_(credit_by_user.keys())).all()
            for u in users:
                u.balance = (u.balance or 0.0) + credit_by_user[u.id]

        # 3️⃣ Mark market resolved
        market.resolved = True
        market.outcome = outcome_upper
        # Optional: store the resolution note in description if you want to display later
        if market.description:
            market.description += f"\n\n🟢 {resolution_note}"
        else:
            market.description = resolution_note

        db.commit()

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resolve market and credit winners: {str(e)}")

    # Return final state
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
        price_no=p_no,
        created_at=market.created_at,
        expires_at=market.expires_at
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


@app.get("/markets/{market_id}/history")
def get_price_history(market_id: int, db: Session = Depends(get_db)):
    records = (
        db.query(PriceHistory)
        .filter(PriceHistory.market_id == market_id)
        .order_by(PriceHistory.timestamp.asc())
        .all()
    )
    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "price_yes": r.price_yes,
            "price_no": r.price_no,
        }
        for r in records
    ]

@app.get("/markets/{market_id}/leaderboard")
def get_leaderboard(market_id: int, db: Session = Depends(get_db)):
    """Return a leaderboard for a given market, including all users with any stake,
    even if payout is 0. Shows YES/NO shares, total spent, average price, and PnL."""
    from sqlalchemy import func

    # Get market outcome (if resolved)
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    bets = db.query(Bet).filter(Bet.market_id == market_id).all()
    if not bets:
        return []

    leaderboard = {}
    for bet in bets:
        u = bet.user_id
        if u not in leaderboard:
            leaderboard[u] = {
                "username": bet.user.username,
                "yes_shares": 0.0,
                "no_shares": 0.0,
                "spent": 0.0,
                "payout": 0.0,
                "avg_price_yes": None,
                "avg_price_no": None,
                "_price_sum_yes": 0.0,
                "_price_sum_no": 0.0,
                "_share_sum_yes": 0.0,
                "_share_sum_no": 0.0,
            }
        if bet.side == "YES":
            leaderboard[u]["yes_shares"] += bet.amount
            leaderboard[u]["spent"] += bet.total_cost
            leaderboard[u]["_price_sum_yes"] += bet.price * bet.amount
            leaderboard[u]["_share_sum_yes"] += bet.amount
        else:
            leaderboard[u]["no_shares"] += bet.amount
            leaderboard[u]["spent"] += bet.total_cost
            leaderboard[u]["_price_sum_no"] += bet.price * bet.amount
            leaderboard[u]["_share_sum_no"] += bet.amount

    # Compute average prices and payouts
    for u, row in leaderboard.items():
        if row["_share_sum_yes"] > 0:
            row["avg_price_yes"] = row["_price_sum_yes"] / row["_share_sum_yes"]
        if row["_share_sum_no"] > 0:
            row["avg_price_no"] = row["_price_sum_no"] / row["_share_sum_no"]

        if market.resolved:
            if market.outcome == "YES":
                row["payout"] = row["yes_shares"] * 1.0 - row["spent"]
            else:
                row["payout"] = row["no_shares"] * 1.0 - row["spent"]
        else:
            # unrealized PnL — could be computed using latest LMSR prices later
            row["payout"] = -row["spent"]

        # cleanup helper keys
        for key in list(row.keys()):
            if key.startswith("_"):
                del row[key]

    return list(leaderboard.values())

@app.get("/user/{user_id}/bets")
def get_user_bets(user_id: int, db: Session = Depends(get_db)):
    """Return full betting history for a user across all markets, with realized/unrealized PnL."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bets = (
        db.query(Bet)
        .filter(Bet.user_id == user_id)
        .order_by(Bet.timestamp.desc())
        .all()
    )
    if not bets:
        return {"bets": [], "lifetime_pnl": 0.0}

    # Get all markets for reference
    market_ids = list({b.market_id for b in bets})
    markets = {m.id: m for m in db.query(Market).filter(Market.id.in_(market_ids)).all()}

    history = []
    lifetime_pnl = 0.0

    for b in bets:
        m = markets.get(b.market_id)
        if not m:
            continue

        # Calculate PnL
        if m.resolved:
            realized_pnl = b.amount * (1.0 if b.side == m.outcome else 0.0) - b.total_cost
        else:
            # Unrealized PnL = current LMSR mark-to-market (optional simplification)
            realized_pnl = -b.total_cost
        lifetime_pnl += realized_pnl

        history.append({
            "market_title": m.title,
            "side": b.side,
            "amount": b.amount,
            "price": b.price,
            "total_cost": b.total_cost,
            "timestamp": b.timestamp.isoformat(),
            "resolved": m.resolved,
            "outcome": m.outcome,
            "pnl": realized_pnl
        })

    return {"bets": history, "lifetime_pnl": lifetime_pnl}

class PasswordChangeRequest(BaseModel):
    user_id: int
    old_password: str
    new_password: str

@app.post("/user/change_password")
def change_password(req: PasswordChangeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user or not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}

@app.post("/user/{user_id}/claim_bonus")
def claim_daily_bonus(user_id: int, db: Session = Depends(get_db)):
    """Allow a user to claim 50 credits every 23 hours if balance ≤ 500."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)

    # Normalize stored timestamp to UTC if naive
    if user.last_bonus_claim and user.last_bonus_claim.tzinfo is None:
        user.last_bonus_claim = user.last_bonus_claim.replace(tzinfo=timezone.utc)

    # Check last claim time
    if user.last_bonus_claim:
        elapsed = now - user.last_bonus_claim
        if elapsed < timedelta(hours=23):
            remaining = timedelta(hours=23) - elapsed
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            raise HTTPException(
                status_code=400,
                detail=f"Bonus already claimed. Try again in {hours}h {mins}m."
            )

    # Check balance limit
    if user.balance > 500:
        raise HTTPException(status_code=400, detail="Balance too high to claim bonus (must be ≤ 500).")

    # Apply bonus
    user.balance += 50
    user.last_bonus_claim = now
    db.commit()
    return {"detail": f"✅ Bonus claimed! +50 credits added. New balance: {user.balance:.2f}"}


@app.get("/")
def root():
    return {"message": "Prediction Market API is running!"}

