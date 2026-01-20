"""US Stock data API endpoints using Finnhub API."""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio
import logging

from app.database import get_db
from app.models.us_stock import USStock, USFinancialData
from app.config import get_settings

logger = logging.getLogger(__name__)

# Global state for tracking batch scrape progress
_us_scrape_progress: Dict[str, Any] = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_symbol": "",
    "success_count": 0,
    "failed_count": 0,
    "started_at": None,
    "results": None,
}

router = APIRouter(prefix="/us-stocks", tags=["US Stocks"])


# ============================================================================
# Response Models
# ============================================================================

class USStockPrice(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[int] = None
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    # Valuation data (cached)
    sticker_price: Optional[float] = None
    margin_of_safety: Optional[float] = None
    discount_pct: Optional[float] = None
    four_m_score: Optional[float] = None
    four_m_grade: Optional[str] = None
    big_five_score: Optional[int] = None
    big_five_warning: bool = False
    recommendation: Optional[str] = None
    valuation_status: str = "UNKNOWN"
    valuation_note: Optional[str] = None
    is_sp500: bool = False
    last_fundamental_update: Optional[datetime] = None


class USFinancialRecord(BaseModel):
    year: int
    revenue: Optional[int] = None
    net_income: Optional[int] = None
    eps: Optional[float] = None
    total_equity: Optional[int] = None
    total_assets: Optional[int] = None
    total_debt: Optional[int] = None
    operating_cash_flow: Optional[int] = None
    capital_expenditure: Optional[int] = None
    free_cash_flow: Optional[int] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None


class ScrapeStatusResponse(BaseModel):
    running: bool
    current: int
    total: int
    current_symbol: str
    success_count: int
    failed_count: int
    progress_percent: Optional[float] = None
    started_at: Optional[str] = None
    completed: bool = False


class SeedRequest(BaseModel):
    sp500_only: bool = False


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/prices", response_model=List[USStockPrice])
def get_all_us_prices(
    limit: int = Query(default=500, le=5000),
    offset: int = Query(default=0, ge=0),
    sp500_only: bool = Query(default=False),
    sector: Optional[str] = Query(default=None),
    has_valuation: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """Get all US stocks with cached prices and valuations.

    Args:
        limit: Maximum number of stocks to return (max 5000)
        offset: Offset for pagination
        sp500_only: If True, only return S&P 500 stocks
        sector: Filter by sector
        has_valuation: If True, only return stocks with calculated valuations
    """
    query = db.query(USStock)

    if sp500_only:
        query = query.filter(USStock.is_sp500 == True)

    if sector:
        query = query.filter(USStock.sector == sector)

    if has_valuation:
        query = query.filter(USStock.valuation_status == "CALCULABLE")

    # Order by market cap (largest first), then by symbol
    query = query.order_by(USStock.market_cap.desc().nullslast(), USStock.symbol)

    stocks = query.offset(offset).limit(limit).all()

    result = []
    for stock in stocks:
        # Calculate live discount percentage
        discount_pct = None
        if stock.sticker_price and stock.current_price and stock.sticker_price > 0:
            discount_pct = ((stock.current_price - stock.sticker_price) / stock.sticker_price) * 100

        result.append(USStockPrice(
            symbol=stock.symbol,
            name=stock.name,
            sector=stock.sector,
            market_cap=stock.market_cap,
            current_price=stock.current_price,
            previous_close=stock.previous_close,
            change=stock.change,
            change_pct=stock.change_pct,
            high_52w=stock.high_52w,
            low_52w=stock.low_52w,
            sticker_price=stock.sticker_price,
            margin_of_safety=stock.margin_of_safety,
            discount_pct=round(discount_pct, 2) if discount_pct is not None else None,
            four_m_score=stock.four_m_score,
            four_m_grade=stock.four_m_grade,
            big_five_score=stock.big_five_score,
            big_five_warning=stock.big_five_warning or False,
            recommendation=stock.recommendation,
            valuation_status=stock.valuation_status or "UNKNOWN",
            valuation_note=stock.valuation_note,
            is_sp500=stock.is_sp500 or False,
            last_fundamental_update=stock.last_fundamental_update,
        ))

    return result


@router.get("/count")
def get_us_stock_count(
    sp500_only: bool = Query(default=False),
    has_valuation: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """Get total count of US stocks."""
    query = db.query(USStock)

    if sp500_only:
        query = query.filter(USStock.is_sp500 == True)

    if has_valuation:
        query = query.filter(USStock.valuation_status == "CALCULABLE")

    total = query.count()

    return {
        "total": total,
        "sp500_only": sp500_only,
        "has_valuation": has_valuation,
    }


@router.get("/sectors")
def get_us_sectors(db: Session = Depends(get_db)):
    """Get list of unique sectors."""
    result = db.execute(
        text("SELECT DISTINCT sector FROM us_stocks WHERE sector IS NOT NULL ORDER BY sector")
    )
    sectors = [row[0] for row in result.fetchall()]
    return {"sectors": sectors}


@router.get("/{symbol}/fundamentals")
def get_us_stock_fundamentals(symbol: str, db: Session = Depends(get_db)):
    """Get fundamental data for a US stock."""
    financials = db.query(USFinancialData).filter(
        USFinancialData.stock_symbol == symbol.upper()
    ).order_by(USFinancialData.year.desc()).all()

    if not financials:
        raise HTTPException(
            status_code=404,
            detail=f"No financial data found for {symbol}. Try triggering a scrape first."
        )

    return {
        "symbol": symbol.upper(),
        "source": "finnhub",
        "data": [
            USFinancialRecord(
                year=f.year,
                revenue=f.revenue,
                net_income=f.net_income,
                eps=f.eps,
                total_equity=f.total_equity,
                total_assets=f.total_assets,
                total_debt=f.total_debt,
                operating_cash_flow=f.operating_cash_flow,
                capital_expenditure=f.capital_expenditure,
                free_cash_flow=f.free_cash_flow,
                roe=f.roe,
                roa=f.roa,
                debt_to_equity=f.debt_to_equity,
                gross_margin=f.gross_margin,
                operating_margin=f.operating_margin,
                net_margin=f.net_margin,
            ).model_dump()
            for f in sorted(financials, key=lambda x: x.year)
        ],
    }


# ============================================================================
# Seed and Scrape Endpoints
# ============================================================================

@router.post("/seed")
async def seed_us_stocks(
    request: SeedRequest = None,
    db: Session = Depends(get_db)
):
    """Seed US stock symbols from Finnhub API.

    This fetches all US stock symbols and populates the us_stocks table.
    S&P 500 stocks are marked with is_sp500=True.
    """
    settings = get_settings()

    if not settings.finnhub_api_key:
        raise HTTPException(
            status_code=500,
            detail="FINNHUB_API_KEY not configured. Set it in environment variables."
        )

    try:
        from app.services.finnhub_service import FinnhubService, SP500_SYMBOLS

        async with FinnhubService(settings.finnhub_api_key) as service:
            # Fetch all US symbols
            symbols = await service.get_all_us_symbols()

            if request and request.sp500_only:
                # Filter to S&P 500 only
                symbols = [s for s in symbols if s.get("symbol") in SP500_SYMBOLS]

            # Get all existing symbols in ONE query for performance
            existing_symbols = set(
                row[0] for row in db.query(USStock.symbol).all()
            )

            # Prepare bulk insert list
            new_stocks = []
            skipped = 0

            for sym_data in symbols:
                symbol = sym_data.get("symbol", "")

                # Skip invalid symbols (contain special characters)
                if not symbol or "." in symbol or "-" in symbol or len(symbol) > 10:
                    skipped += 1
                    continue

                # Skip if already exists
                if symbol in existing_symbols:
                    continue

                is_sp500 = symbol in SP500_SYMBOLS

                new_stocks.append(USStock(
                    symbol=symbol,
                    name=sym_data.get("description"),
                    is_sp500=is_sp500,
                    scrape_priority=10 if is_sp500 else 100,
                    valuation_status="UNKNOWN",
                ))

            # Bulk insert all new stocks
            if new_stocks:
                db.bulk_save_objects(new_stocks)
                db.commit()

            return {
                "message": f"Seeded US stocks successfully",
                "total_fetched": len(symbols),
                "inserted": len(new_stocks),
                "skipped": skipped,
                "already_existed": len(existing_symbols),
                "sp500_count": len(SP500_SYMBOLS),
            }

    except Exception as e:
        logger.error(f"Error seeding US stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-scrape")
async def trigger_us_scrape(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(default=None),
    sp500_only: bool = Query(default=False),
    symbol: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Trigger scraping of US stock data from Finnhub.

    Runs in background. Fetches financials, quotes, and calculates valuations.

    Args:
        batch_size: Number of stocks to scrape (default from settings)
        sp500_only: If True, only scrape S&P 500 stocks
        symbol: If provided, only scrape this specific symbol
    """
    global _us_scrape_progress

    if _us_scrape_progress["running"]:
        return {
            "status": "already_running",
            "message": "US stock scrape already in progress",
            "progress": {
                "current": _us_scrape_progress["current"],
                "total": _us_scrape_progress["total"],
                "current_symbol": _us_scrape_progress["current_symbol"],
            }
        }

    settings = get_settings()

    if not settings.finnhub_api_key:
        raise HTTPException(
            status_code=500,
            detail="FINNHUB_API_KEY not configured"
        )

    batch_size = batch_size or settings.us_scrape_batch_size

    # Get stocks to scrape
    if symbol:
        stocks = db.query(USStock).filter(USStock.symbol == symbol.upper()).all()
    else:
        query = db.query(USStock)

        if sp500_only:
            query = query.filter(USStock.is_sp500 == True)

        # Priority queue: never scraped first, then oldest updates
        query = query.order_by(
            USStock.last_fundamental_update.asc().nullsfirst(),
            USStock.scrape_priority.asc()
        )

        stocks = query.limit(batch_size).all()

    if not stocks:
        raise HTTPException(
            status_code=400,
            detail="No stocks to scrape. Run /us-stocks/seed first."
        )

    symbols = [s.symbol for s in stocks]

    # Reset progress
    _us_scrape_progress = {
        "running": True,
        "current": 0,
        "total": len(symbols),
        "current_symbol": "",
        "success_count": 0,
        "failed_count": 0,
        "started_at": datetime.now().isoformat(),
        "results": None,
    }

    # Start background task
    background_tasks.add_task(_run_us_scrape, symbols, settings.finnhub_api_key)

    return {
        "status": "started",
        "message": f"Started scraping {len(symbols)} US stocks in background",
        "total_stocks": len(symbols),
        "symbols_sample": symbols[:10],
        "check_progress_at": "/us-stocks/scrape-status"
    }


@router.get("/scrape-status", response_model=ScrapeStatusResponse)
def get_us_scrape_status():
    """Get current status of US stock scraping."""
    global _us_scrape_progress

    progress_percent = None
    if _us_scrape_progress["total"] > 0:
        progress_percent = round(
            _us_scrape_progress["current"] / _us_scrape_progress["total"] * 100, 1
        )

    return ScrapeStatusResponse(
        running=_us_scrape_progress["running"],
        current=_us_scrape_progress["current"],
        total=_us_scrape_progress["total"],
        current_symbol=_us_scrape_progress["current_symbol"],
        success_count=_us_scrape_progress["success_count"],
        failed_count=_us_scrape_progress["failed_count"],
        progress_percent=progress_percent,
        started_at=_us_scrape_progress["started_at"],
        completed=not _us_scrape_progress["running"] and _us_scrape_progress["results"] is not None,
    )


@router.post("/stop-scrape")
def stop_us_scrape():
    """Stop the running US stock scrape."""
    global _us_scrape_progress

    if not _us_scrape_progress["running"]:
        return {"status": "not_running", "message": "No scrape is running"}

    _us_scrape_progress["running"] = False

    return {
        "status": "stopping",
        "message": "Scrape will stop after current stock completes",
        "scraped_so_far": _us_scrape_progress["current"],
    }


# ============================================================================
# Background Scrape Task
# ============================================================================

async def _run_us_scrape(symbols: List[str], api_key: str):
    """Background task to scrape US stock data."""
    global _us_scrape_progress

    from app.database import SessionLocal
    from app.services.finnhub_service import FinnhubService

    db = SessionLocal()

    try:
        async with FinnhubService(api_key) as service:
            results = {"success": [], "failed": []}

            for i, symbol in enumerate(symbols):
                if not _us_scrape_progress["running"]:
                    logger.info("US scrape stopped by user")
                    break

                _us_scrape_progress["current_symbol"] = symbol

                try:
                    # Scrape data
                    data = await service.scrape_stock(symbol)

                    # Save to database
                    _save_us_stock_data(db, symbol, data)

                    # Calculate valuations
                    _calculate_us_valuations(db, symbol)

                    results["success"].append(symbol)
                    _us_scrape_progress["success_count"] += 1

                except Exception as e:
                    logger.error(f"Error scraping {symbol}: {e}")
                    results["failed"].append({"symbol": symbol, "error": str(e)})
                    _us_scrape_progress["failed_count"] += 1

                _us_scrape_progress["current"] = i + 1

                # Small delay between stocks (rate limiter handles most)
                if i < len(symbols) - 1:
                    await asyncio.sleep(0.5)

            results["completed_at"] = datetime.now().isoformat()
            _us_scrape_progress["results"] = results

    except Exception as e:
        logger.error(f"US scrape error: {e}")
        _us_scrape_progress["results"] = {"error": str(e)}

    finally:
        _us_scrape_progress["running"] = False
        db.close()


def _save_us_stock_data(db: Session, symbol: str, data: Dict):
    """Save scraped Finnhub data to database."""
    stock = db.query(USStock).filter(USStock.symbol == symbol).first()

    if not stock:
        stock = USStock(symbol=symbol)
        db.add(stock)

    # Update quote data
    if data.get("quote"):
        quote = data["quote"]
        stock.current_price = quote.get("current_price")
        stock.previous_close = quote.get("previous_close")
        stock.change = quote.get("change")
        stock.change_pct = quote.get("change_pct")
        stock.last_price_update = datetime.now()

    # Update profile data
    if data.get("profile"):
        profile = data["profile"]
        stock.name = profile.get("name") or stock.name
        stock.sector = profile.get("sector") or stock.sector
        # Market cap comes in millions, convert to actual
        if profile.get("market_cap"):
            stock.market_cap = int(profile["market_cap"] * 1_000_000)

    # Update metrics
    if data.get("metrics"):
        metrics = data["metrics"]
        stock.high_52w = metrics.get("high_52w")
        stock.low_52w = metrics.get("low_52w")

    # Save financial data
    if data.get("financials"):
        for year, fin_data in data["financials"].items():
            if not isinstance(year, int):
                try:
                    year = int(year)
                except:
                    continue

            existing = db.query(USFinancialData).filter(
                USFinancialData.stock_symbol == symbol,
                USFinancialData.year == year
            ).first()

            if not existing:
                existing = USFinancialData(stock_symbol=symbol, year=year)
                db.add(existing)

            # Update fields
            for field in ["revenue", "net_income", "eps", "total_equity",
                         "total_assets", "total_liabilities", "total_debt",
                         "operating_cash_flow", "capital_expenditure", "gross_profit",
                         "operating_income"]:
                if field in fin_data:
                    setattr(existing, field, fin_data[field])

            # Calculate derived metrics
            _calculate_financial_ratios(existing)

    stock.last_fundamental_update = datetime.now()
    stock.updated_at = datetime.now()

    db.commit()


def _calculate_financial_ratios(record: USFinancialData):
    """Calculate financial ratios from raw data."""
    # Free Cash Flow
    if record.operating_cash_flow and record.capital_expenditure:
        record.free_cash_flow = record.operating_cash_flow - abs(record.capital_expenditure)

    # ROE
    if record.net_income and record.total_equity and record.total_equity > 0:
        record.roe = (record.net_income / record.total_equity) * 100

    # ROA
    if record.net_income and record.total_assets and record.total_assets > 0:
        record.roa = (record.net_income / record.total_assets) * 100

    # Debt to Equity
    if record.total_debt is not None and record.total_equity and record.total_equity > 0:
        record.debt_to_equity = record.total_debt / record.total_equity

    # Margins
    if record.revenue and record.revenue > 0:
        if record.gross_profit:
            record.gross_margin = (record.gross_profit / record.revenue) * 100
        if record.operating_income:
            record.operating_margin = (record.operating_income / record.revenue) * 100
        if record.net_income:
            record.net_margin = (record.net_income / record.revenue) * 100


def _calculate_us_valuations(db: Session, symbol: str):
    """Calculate Phil Town valuations for a US stock."""
    from app.calculations import StickerPriceCalculator, BigFiveCalculator, FourMsEvaluator

    stock = db.query(USStock).filter(USStock.symbol == symbol).first()
    if not stock:
        return

    # Get financial data
    financials = db.query(USFinancialData).filter(
        USFinancialData.stock_symbol == symbol
    ).order_by(USFinancialData.year.asc()).all()

    if len(financials) < 3:
        stock.valuation_status = "NOT_CALCULABLE"
        stock.valuation_note = "Insufficient financial data (need 3+ years)"
        db.commit()
        return

    try:
        # Prepare data for calculations
        fin_data = []
        for f in financials:
            fin_data.append({
                "year": f.year,
                "eps": f.eps,
                "revenue": f.revenue,
                "total_equity": f.total_equity,
                "operating_cash_flow": f.operating_cash_flow,
                "free_cash_flow": f.free_cash_flow,
                "roe": f.roe,
                "debt_to_equity": f.debt_to_equity,
                "gross_margin": f.gross_margin,
                "operating_margin": f.operating_margin,
                "net_income": f.net_income,
            })

        # Calculate Big Five
        big_five_calc = BigFiveCalculator()
        big_five_result = big_five_calc.calculate(fin_data)
        stock.big_five_score = big_five_result.score
        stock.big_five_warning = not big_five_result.passes  # Warn if score < 3

        # Calculate Sticker Price
        eps_history = [f.eps for f in financials if f.eps is not None]
        if len(eps_history) < 2:
            stock.valuation_status = "NOT_CALCULABLE"
            stock.valuation_note = "Missing EPS data for sticker price calculation"
            db.commit()
            return

        # Get average PE from metrics or use default
        pe_avg = 15.0  # Default PE
        sticker_calc = StickerPriceCalculator()
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_history,
            historical_pe=pe_avg,
            current_price=stock.current_price
        )

        if sticker_result.status == "CALCULABLE":
            stock.sticker_price = sticker_result.sticker_price
            stock.margin_of_safety = sticker_result.margin_of_safety
            stock.discount_to_sticker = sticker_result.discount_to_sticker

            # Calculate 4Ms
            four_ms_eval = FourMsEvaluator()
            four_ms_result = four_ms_eval.evaluate(
                financial_data=fin_data,
                current_price=stock.current_price,
                sticker_price=sticker_result.sticker_price,
                margin_of_safety=sticker_result.margin_of_safety,
                big_five_score=big_five_result.score,
            )

            stock.four_m_score = four_ms_result.overall_score
            stock.four_m_grade = four_ms_result.overall_grade

            # Determine recommendation
            stock.recommendation = _get_recommendation(
                stock.discount_to_sticker,
                stock.big_five_warning,
                stock.four_m_grade
            )

            stock.valuation_status = "CALCULABLE"
            stock.valuation_note = None
        else:
            stock.valuation_status = "NOT_CALCULABLE"
            stock.valuation_note = sticker_result.note or "Could not calculate sticker price"

        stock.last_valuation_update = datetime.now()
        db.commit()

    except Exception as e:
        logger.error(f"Error calculating valuations for {symbol}: {e}")
        stock.valuation_status = "NOT_CALCULABLE"
        stock.valuation_note = f"Calculation error: {str(e)}"
        db.commit()


def _get_recommendation(discount_pct: Optional[float], big_five_warning: bool, grade: Optional[str]) -> str:
    """Determine investment recommendation."""
    if discount_pct is None:
        return "HOLD"

    # Cap at HOLD if Big Five fails
    if big_five_warning:
        if discount_pct <= -50:
            return "HOLD"  # Would be STRONG_BUY but capped due to Big Five
        return "HOLD"

    # Normal recommendation logic
    if discount_pct <= -50:
        return "STRONG_BUY"
    elif discount_pct <= -30:
        return "BUY"
    elif discount_pct <= 30:
        return "HOLD"
    elif discount_pct <= 50:
        return "SELL"
    else:
        return "STRONG_SELL"


# ============================================================================
# Single Stock Route (MUST be at end to avoid matching /scrape-status etc)
# ============================================================================

@router.get("/{symbol}", response_model=USStockPrice)
def get_us_stock_price(symbol: str, db: Session = Depends(get_db)):
    """Get details for a specific US stock."""
    stock = db.query(USStock).filter(USStock.symbol == symbol.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail=f"US stock {symbol} not found")

    # Calculate live discount percentage
    discount_pct = None
    if stock.sticker_price and stock.current_price and stock.sticker_price > 0:
        discount_pct = ((stock.current_price - stock.sticker_price) / stock.sticker_price) * 100

    return USStockPrice(
        symbol=stock.symbol,
        name=stock.name,
        sector=stock.sector,
        market_cap=stock.market_cap,
        current_price=stock.current_price,
        previous_close=stock.previous_close,
        change=stock.change,
        change_pct=stock.change_pct,
        high_52w=stock.high_52w,
        low_52w=stock.low_52w,
        sticker_price=stock.sticker_price,
        margin_of_safety=stock.margin_of_safety,
        discount_pct=round(discount_pct, 2) if discount_pct is not None else None,
        four_m_score=stock.four_m_score,
        four_m_grade=stock.four_m_grade,
        big_five_score=stock.big_five_score,
        big_five_warning=stock.big_five_warning or False,
        recommendation=stock.recommendation,
        valuation_status=stock.valuation_status or "UNKNOWN",
        valuation_note=stock.valuation_note,
        is_sp500=stock.is_sp500 or False,
        last_fundamental_update=stock.last_fundamental_update,
    )
