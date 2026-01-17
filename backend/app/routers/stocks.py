"""Stock data API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Stock, FinancialData
from app.services import DSEDataService

router = APIRouter(prefix="/stocks", tags=["Stocks"])


class StockPrice(BaseModel):
    symbol: str
    ltp: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None


class StockDetail(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    current_price: Optional[float] = None
    sticker_price: Optional[float] = None
    margin_of_safety: Optional[float] = None
    recommendation: Optional[str] = None
    big_five_score: Optional[int] = None


class FinancialRecord(BaseModel):
    year: int
    revenue: Optional[float] = None
    eps: Optional[float] = None
    total_equity: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None


@router.get("/prices", response_model=List[StockPrice])
def get_all_prices(limit: int = Query(default=50, le=500)):
    """Get current prices for all DSE stocks."""
    data_service = DSEDataService()
    df = data_service.get_current_prices()

    if df.empty:
        raise HTTPException(status_code=503, detail="Could not fetch price data")

    prices = []
    for _, row in df.head(limit).iterrows():
        price = StockPrice(
            symbol=str(row.get('trading_code', row.get('symbol', ''))),
            ltp=_safe_float(row.get('ltp', row.get('close'))),
            high=_safe_float(row.get('high')),
            low=_safe_float(row.get('low')),
            open=_safe_float(row.get('open')),
            close=_safe_float(row.get('close', row.get('ltp'))),
            volume=_safe_int(row.get('volume', row.get('trade'))),
            change=_safe_float(row.get('change', row.get('closep'))),
            change_pct=_safe_float(row.get('change_%', row.get('%change'))),
        )
        prices.append(price)

    return prices


@router.get("/{symbol}", response_model=StockPrice)
def get_stock_price(symbol: str):
    """Get current price for a specific stock."""
    data_service = DSEDataService()
    price_data = data_service.get_stock_price(symbol.upper())

    if not price_data:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    return StockPrice(
        symbol=symbol.upper(),
        ltp=_safe_float(price_data.get('ltp', price_data.get('close'))),
        high=_safe_float(price_data.get('high')),
        low=_safe_float(price_data.get('low')),
        open=_safe_float(price_data.get('open')),
        close=_safe_float(price_data.get('close', price_data.get('ltp'))),
        volume=_safe_int(price_data.get('volume', price_data.get('trade'))),
        change=_safe_float(price_data.get('change', price_data.get('closep'))),
        change_pct=_safe_float(price_data.get('change_%', price_data.get('%change'))),
    )


@router.get("/{symbol}/history")
def get_stock_history(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get historical price data for a stock."""
    data_service = DSEDataService()
    df = data_service.get_historical_prices(symbol.upper(), start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No history found for {symbol}")

    # Convert to list of dicts
    records = df.to_dict('records')
    return {
        "symbol": symbol.upper(),
        "count": len(records),
        "data": records,
    }


@router.get("/{symbol}/fundamentals")
def get_stock_fundamentals(symbol: str, db: Session = Depends(get_db)):
    """Get fundamental data for a stock.

    First checks database, then fetches from external source if needed.
    """
    # Check if we have recent data in database
    financials = db.query(FinancialData).filter(
        FinancialData.stock_symbol == symbol.upper()
    ).order_by(FinancialData.year.desc()).all()

    if financials and len(financials) >= 3:
        # Return cached data
        return {
            "symbol": symbol.upper(),
            "source": "database",
            "data": [
                FinancialRecord(
                    year=f.year,
                    revenue=f.revenue,
                    eps=f.eps,
                    total_equity=f.total_equity,
                    operating_cash_flow=f.operating_cash_flow,
                    free_cash_flow=f.free_cash_flow,
                    roe=f.roe,
                    debt_to_equity=f.debt_to_equity,
                ).model_dump()
                for f in sorted(financials, key=lambda x: x.year)
            ],
        }

    # Fetch from external source
    data_service = DSEDataService()
    raw_data = data_service.get_fundamental_data(symbol.upper())

    if not raw_data.get("success"):
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch fundamentals for {symbol}: {raw_data.get('error', 'Unknown error')}"
        )

    # Parse the data
    parsed_data = data_service.parse_financial_data(raw_data)

    # Save to database for caching
    for record in parsed_data:
        # Check if exists
        existing = db.query(FinancialData).filter(
            FinancialData.stock_symbol == symbol.upper(),
            FinancialData.year == record["year"]
        ).first()

        if existing:
            # Update
            for key, value in record.items():
                if key != "year" and value is not None:
                    setattr(existing, key, value)
        else:
            # Create new
            financial = FinancialData(
                stock_symbol=symbol.upper(),
                source="stocksurferbd",
                **record
            )
            db.add(financial)

    db.commit()

    return {
        "symbol": symbol.upper(),
        "source": "stocksurferbd",
        "company_data": raw_data.get("company_data", {}),
        "data": parsed_data,
    }


@router.post("/{symbol}/refresh-fundamentals")
def refresh_fundamentals(symbol: str, db: Session = Depends(get_db)):
    """Force refresh fundamental data from external source."""
    data_service = DSEDataService()
    raw_data = data_service.get_fundamental_data(symbol.upper())

    if not raw_data.get("success"):
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch fundamentals for {symbol}"
        )

    # Parse and update database
    parsed_data = data_service.parse_financial_data(raw_data)

    for record in parsed_data:
        existing = db.query(FinancialData).filter(
            FinancialData.stock_symbol == symbol.upper(),
            FinancialData.year == record["year"]
        ).first()

        if existing:
            for key, value in record.items():
                if key != "year" and value is not None:
                    setattr(existing, key, value)
            existing.source = "stocksurferbd"
        else:
            financial = FinancialData(
                stock_symbol=symbol.upper(),
                source="stocksurferbd",
                **record
            )
            db.add(financial)

    db.commit()

    return {
        "message": f"Refreshed fundamentals for {symbol}",
        "years_updated": len(parsed_data),
    }


def _safe_float(val) -> Optional[float]:
    """Safely convert value to float."""
    if val is None or val == '':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    """Safely convert value to int."""
    if val is None or val == '':
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None
