"""Portfolio API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import PortfolioHolding, Stock
from app.services import DSEDataService

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


# Pydantic models for request/response
class HoldingCreate(BaseModel):
    stock_symbol: str
    shares: int
    avg_cost: float
    notes: Optional[str] = None
    buy_date: Optional[datetime] = None


class HoldingUpdate(BaseModel):
    shares: Optional[int] = None
    avg_cost: Optional[float] = None
    notes: Optional[str] = None


class HoldingResponse(BaseModel):
    id: int
    stock_symbol: str
    shares: int
    avg_cost: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    total_cost: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_invested: float
    current_value: float
    total_profit_loss: float
    total_profit_loss_pct: float
    holdings_count: int
    holdings: List[HoldingResponse]


@router.get("/", response_model=PortfolioSummary)
def get_portfolio(db: Session = Depends(get_db)):
    """Get full portfolio with live P&L calculations."""
    holdings = db.query(PortfolioHolding).all()

    # Fetch current prices
    data_service = DSEDataService()

    total_invested = 0.0
    current_value = 0.0
    holdings_response = []

    for holding in holdings:
        # Calculate total cost
        holding.total_cost = holding.shares * holding.avg_cost
        total_invested += holding.total_cost

        # Get current price
        price_data = data_service.get_stock_price(holding.stock_symbol)
        if price_data:
            # Try different field names for price
            current_price = None
            for key in ['ltp', 'close', 'last_trade_price', 'price', 'close_price']:
                if key in price_data and price_data[key]:
                    try:
                        current_price = float(price_data[key])
                        break
                    except (ValueError, TypeError):
                        continue

            if current_price:
                holding.current_value = holding.shares * current_price
                holding.profit_loss = holding.current_value - holding.total_cost
                holding.profit_loss_pct = (holding.profit_loss / holding.total_cost) * 100 if holding.total_cost else 0
                current_value += holding.current_value

                holdings_response.append(HoldingResponse(
                    id=holding.id,
                    stock_symbol=holding.stock_symbol,
                    shares=holding.shares,
                    avg_cost=holding.avg_cost,
                    current_price=current_price,
                    current_value=holding.current_value,
                    total_cost=holding.total_cost,
                    profit_loss=holding.profit_loss,
                    profit_loss_pct=holding.profit_loss_pct,
                    notes=holding.notes,
                ))
            else:
                # No price available
                holdings_response.append(HoldingResponse(
                    id=holding.id,
                    stock_symbol=holding.stock_symbol,
                    shares=holding.shares,
                    avg_cost=holding.avg_cost,
                    total_cost=holding.total_cost,
                    notes=holding.notes,
                ))
        else:
            holdings_response.append(HoldingResponse(
                id=holding.id,
                stock_symbol=holding.stock_symbol,
                shares=holding.shares,
                avg_cost=holding.avg_cost,
                total_cost=holding.total_cost,
                notes=holding.notes,
            ))

    # Calculate summary
    total_pnl = current_value - total_invested
    total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested else 0

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        current_value=round(current_value, 2),
        total_profit_loss=round(total_pnl, 2),
        total_profit_loss_pct=round(total_pnl_pct, 2),
        holdings_count=len(holdings),
        holdings=holdings_response,
    )


@router.post("/", response_model=HoldingResponse)
def add_holding(holding: HoldingCreate, db: Session = Depends(get_db)):
    """Add a new holding to the portfolio."""
    # Check if stock exists in database, if not create it
    stock = db.query(Stock).filter(Stock.symbol == holding.stock_symbol.upper()).first()
    if not stock:
        stock = Stock(symbol=holding.stock_symbol.upper())
        db.add(stock)
        db.commit()

    # Check if holding already exists
    existing = db.query(PortfolioHolding).filter(
        PortfolioHolding.stock_symbol == holding.stock_symbol.upper()
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Holding for {holding.stock_symbol} already exists. Use PUT to update."
        )

    # Create new holding
    db_holding = PortfolioHolding(
        stock_symbol=holding.stock_symbol.upper(),
        shares=holding.shares,
        avg_cost=holding.avg_cost,
        notes=holding.notes,
        buy_date=holding.buy_date,
        total_cost=holding.shares * holding.avg_cost,
    )
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)

    return HoldingResponse(
        id=db_holding.id,
        stock_symbol=db_holding.stock_symbol,
        shares=db_holding.shares,
        avg_cost=db_holding.avg_cost,
        total_cost=db_holding.total_cost,
        notes=db_holding.notes,
    )


@router.put("/{symbol}", response_model=HoldingResponse)
def update_holding(symbol: str, update: HoldingUpdate, db: Session = Depends(get_db)):
    """Update an existing holding."""
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.stock_symbol == symbol.upper()
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail=f"Holding {symbol} not found")

    if update.shares is not None:
        holding.shares = update.shares
    if update.avg_cost is not None:
        holding.avg_cost = update.avg_cost
    if update.notes is not None:
        holding.notes = update.notes

    holding.total_cost = holding.shares * holding.avg_cost

    db.commit()
    db.refresh(holding)

    return HoldingResponse(
        id=holding.id,
        stock_symbol=holding.stock_symbol,
        shares=holding.shares,
        avg_cost=holding.avg_cost,
        total_cost=holding.total_cost,
        notes=holding.notes,
    )


@router.delete("/{symbol}")
def delete_holding(symbol: str, db: Session = Depends(get_db)):
    """Remove a holding from the portfolio."""
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.stock_symbol == symbol.upper()
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail=f"Holding {symbol} not found")

    db.delete(holding)
    db.commit()

    return {"message": f"Holding {symbol} deleted successfully"}


@router.post("/seed")
def seed_portfolio(db: Session = Depends(get_db)):
    """Seed the portfolio with the user's 4 stocks."""
    holdings_data = [
        {"symbol": "BXPHARMA", "shares": 779, "avg_cost": 135.02},
        {"symbol": "SQURPHARMA", "shares": 1215, "avg_cost": 212.17},
        {"symbol": "MARICO", "shares": 14, "avg_cost": 2332.02},
        {"symbol": "OLYMPIC", "shares": 397, "avg_cost": 125.69},
    ]

    added = []
    for h in holdings_data:
        # Check if exists
        existing = db.query(PortfolioHolding).filter(
            PortfolioHolding.stock_symbol == h["symbol"]
        ).first()

        if not existing:
            # Create stock if needed
            stock = db.query(Stock).filter(Stock.symbol == h["symbol"]).first()
            if not stock:
                stock = Stock(symbol=h["symbol"])
                db.add(stock)

            holding = PortfolioHolding(
                stock_symbol=h["symbol"],
                shares=h["shares"],
                avg_cost=h["avg_cost"],
                total_cost=h["shares"] * h["avg_cost"],
            )
            db.add(holding)
            added.append(h["symbol"])

    db.commit()

    return {"message": f"Seeded portfolio", "added": added}
