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

# Global state for tracking seed progress
_seed_progress: Dict[str, Any] = {
    "running": False,
    "fetched": 0,
    "inserted": 0,
    "updated_types": 0,
    "started_at": None,
    "completed_at": None,
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
    filter_type: Optional[str] = Query(default=None),
    sort_by: str = Query(default="market_cap"),
    sort_order: str = Query(default="desc"),
    search: Optional[str] = Query(default=None, description="Search by symbol or company name"),
    db: Session = Depends(get_db)
):
    """Get all US stocks with cached prices and valuations.

    Args:
        limit: Maximum number of stocks to return (max 5000)
        offset: Offset for pagination
        sp500_only: If True, only return S&P 500 stocks
        sector: Filter by sector
        has_valuation: If True, only return stocks with calculated valuations
        filter_type: Filter type (gainers, losers, undervalued, overvalued)
        sort_by: Column to sort by (symbol, current_price, change, change_pct, market_cap, sticker_price, margin_of_safety, discount_pct, four_m_score)
        sort_order: Sort order (asc or desc)
        search: Search term for symbol or company name
    """
    # Only show Common Stock (exclude ETFs, REITs, ADRs, etc.)
    query = db.query(USStock).filter(USStock.stock_type == "Common Stock")

    # Search filter (symbol or name)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (USStock.symbol.ilike(search_term)) |
            (USStock.name.ilike(search_term))
        )

    if sp500_only:
        query = query.filter(USStock.is_sp500 == True)

    if sector:
        query = query.filter(USStock.sector == sector)

    if has_valuation:
        query = query.filter(USStock.valuation_status == "CALCULABLE")

    # Apply filter_type
    if filter_type == "gainers":
        query = query.filter(USStock.change > 0)
    elif filter_type == "losers":
        query = query.filter(USStock.change < 0)
    elif filter_type == "undervalued":
        query = query.filter(
            USStock.valuation_status == "CALCULABLE",
            USStock.sticker_price > 0,
            USStock.current_price.isnot(None),
            USStock.current_price < USStock.sticker_price
        )
    elif filter_type == "overvalued":
        query = query.filter(
            USStock.valuation_status == "CALCULABLE",
            USStock.sticker_price > 0,
            USStock.current_price.isnot(None),
            USStock.current_price > USStock.sticker_price
        )

    # Map sort_by to actual column
    sort_columns = {
        "symbol": USStock.symbol,
        "current_price": USStock.current_price,
        "change": USStock.change,
        "change_pct": USStock.change_pct,
        "market_cap": USStock.market_cap,
        "sticker_price": USStock.sticker_price,
        "margin_of_safety": USStock.margin_of_safety,
        "four_m_score": USStock.four_m_score,
    }

    # Special handling for discount_pct (calculated field)
    if sort_by == "discount_pct":
        # Sort by the ratio of current_price to sticker_price
        # discount_pct = (current_price - sticker_price) / sticker_price * 100
        # Lower ratio = more undervalued
        from sqlalchemy import case, and_
        discount_expr = case(
            (and_(USStock.sticker_price > 0, USStock.current_price.isnot(None)),
             (USStock.current_price - USStock.sticker_price) / USStock.sticker_price),
            else_=None
        )
        if sort_order == "asc":
            query = query.order_by(discount_expr.asc().nullslast(), USStock.symbol)
        else:
            query = query.order_by(discount_expr.desc().nullslast(), USStock.symbol)
    else:
        sort_column = sort_columns.get(sort_by, USStock.market_cap)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc().nullslast(), USStock.symbol)
        else:
            query = query.order_by(sort_column.desc().nullslast(), USStock.symbol)

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
    """Get total count of US stocks (Common Stock only)."""
    # Only count Common Stock (exclude ETFs, REITs, ADRs, etc.)
    query = db.query(USStock).filter(USStock.stock_type == "Common Stock")

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


@router.get("/filter-counts")
def get_us_filter_counts(db: Session = Depends(get_db)):
    """Get counts for all filter categories in one request.

    Returns counts for: total, sp500, gainers, losers, undervalued, overvalued, with_valuation

    Note: discount is calculated as (current_price - sticker_price) / sticker_price * 100
    - Positive discount = overvalued (price above sticker)
    - Negative discount = undervalued (price below sticker)
    """
    # Only count Common Stock (exclude ETFs, REITs, ADRs, etc.)
    result = db.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_sp500 = TRUE THEN 1 ELSE 0 END) as sp500,
            SUM(CASE WHEN change > 0 THEN 1 ELSE 0 END) as gainers,
            SUM(CASE WHEN change < 0 THEN 1 ELSE 0 END) as losers,
            SUM(CASE WHEN
                valuation_status = 'CALCULABLE'
                AND sticker_price > 0
                AND current_price IS NOT NULL
                AND current_price < sticker_price
            THEN 1 ELSE 0 END) as undervalued,
            SUM(CASE WHEN
                valuation_status = 'CALCULABLE'
                AND sticker_price > 0
                AND current_price IS NOT NULL
                AND current_price > sticker_price
            THEN 1 ELSE 0 END) as overvalued,
            SUM(CASE WHEN valuation_status = 'CALCULABLE' THEN 1 ELSE 0 END) as with_valuation
        FROM us_stocks
        WHERE stock_type = 'Common Stock'
    """))
    row = result.fetchone()

    return {
        "total": row[0] if row else 0,
        "sp500": int(row[1] or 0) if row else 0,
        "gainers": int(row[2] or 0) if row else 0,
        "losers": int(row[3] or 0) if row else 0,
        "undervalued": int(row[4] or 0) if row else 0,
        "overvalued": int(row[5] or 0) if row else 0,
        "with_valuation": int(row[6] or 0) if row else 0,
    }


@router.get("/sectors")
def get_us_sectors(db: Session = Depends(get_db)):
    """Get list of unique sectors (from Common Stock only)."""
    result = db.execute(
        text("SELECT DISTINCT sector FROM us_stocks WHERE sector IS NOT NULL AND stock_type = 'Common Stock' ORDER BY sector")
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

async def _seed_stocks_background(sp500_only: bool = False):
    """Background task to seed US stocks from Finnhub."""
    global _seed_progress
    from app.database import SessionLocal

    _seed_progress["running"] = True
    _seed_progress["started_at"] = datetime.now().isoformat()
    _seed_progress["completed_at"] = None
    _seed_progress["fetched"] = 0
    _seed_progress["inserted"] = 0
    _seed_progress["updated_types"] = 0

    db = SessionLocal()
    try:
        settings = get_settings()
        from app.services.finnhub_service import FinnhubService, SP500_SYMBOLS

        async with FinnhubService(settings.finnhub_api_key) as service:
            # Fetch all US symbols
            symbols = await service.get_all_us_symbols()
            _seed_progress["fetched"] = len(symbols)

            if sp500_only:
                symbols = [s for s in symbols if s.get("symbol") in SP500_SYMBOLS]

            # Get all existing symbols in ONE query for performance
            existing_symbols = set(
                row[0] for row in db.query(USStock.symbol).all()
            )

            # Prepare bulk insert list
            new_stocks = []

            # Build a map of symbol -> type for updating existing stocks
            symbol_type_map = {}

            for sym_data in symbols:
                symbol = sym_data.get("symbol", "")
                stock_type = sym_data.get("type", "")

                # Skip invalid symbols (contain special characters)
                if not symbol or "." in symbol or "-" in symbol or len(symbol) > 10:
                    continue

                symbol_type_map[symbol] = stock_type

                # Skip if already exists
                if symbol in existing_symbols:
                    continue

                is_sp500 = symbol in SP500_SYMBOLS

                new_stocks.append(USStock(
                    symbol=symbol,
                    name=sym_data.get("description"),
                    stock_type=stock_type,
                    is_sp500=is_sp500,
                    scrape_priority=10 if is_sp500 else 100,
                    valuation_status="UNKNOWN",
                ))

            # Bulk insert all new stocks
            if new_stocks:
                db.bulk_save_objects(new_stocks)
                db.commit()
                _seed_progress["inserted"] = len(new_stocks)

            # Update existing stocks that don't have stock_type set - use bulk update for speed
            updated_types = 0
            stocks_without_type = db.query(USStock.id, USStock.symbol).filter(USStock.stock_type.is_(None)).all()

            # Batch the updates for better performance
            batch_size = 1000
            update_batch = []
            for stock_id, symbol in stocks_without_type:
                if symbol in symbol_type_map:
                    update_batch.append({"id": stock_id, "stock_type": symbol_type_map[symbol]})
                    updated_types += 1

                # Commit in batches
                if len(update_batch) >= batch_size:
                    db.bulk_update_mappings(USStock, update_batch)
                    db.commit()
                    _seed_progress["updated_types"] = updated_types
                    update_batch = []

            # Commit any remaining
            if update_batch:
                db.bulk_update_mappings(USStock, update_batch)
                db.commit()
                _seed_progress["updated_types"] = updated_types

            logger.info(f"Seed complete: fetched={_seed_progress['fetched']}, inserted={_seed_progress['inserted']}, updated_types={updated_types}")

    except Exception as e:
        logger.error(f"Error in background seed: {e}")
    finally:
        db.close()
        _seed_progress["running"] = False
        _seed_progress["completed_at"] = datetime.now().isoformat()


@router.post("/seed")
async def seed_us_stocks(
    background_tasks: BackgroundTasks,
    request: SeedRequest = None,
):
    """Seed US stock symbols from Finnhub API.

    This fetches all US stock symbols and populates the us_stocks table.
    S&P 500 stocks are marked with is_sp500=True.
    Runs in background to avoid timeout.
    """
    global _seed_progress

    if _seed_progress["running"]:
        return {
            "status": "already_running",
            "message": "Seed operation already in progress",
            "progress": _seed_progress,
        }

    settings = get_settings()
    if not settings.finnhub_api_key:
        raise HTTPException(
            status_code=500,
            detail="FINNHUB_API_KEY not configured. Set it in environment variables."
        )

    sp500_only = request.sp500_only if request else False

    # Start background task
    background_tasks.add_task(_seed_stocks_background, sp500_only)

    return {
        "status": "started",
        "message": "Seed operation started in background",
        "check_progress_at": "/us-stocks/seed-status",
    }


@router.get("/seed-status")
async def get_seed_status():
    """Get the status of the seed operation."""
    return _seed_progress


@router.post("/trigger-scrape")
async def trigger_us_scrape(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(default=None),
    sp500_only: bool = Query(default=False),
    common_stock_only: bool = Query(default=True, description="Only scrape Common Stock type (skip ETFs, ADRs, etc.)"),
    symbol: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Trigger scraping of US stock data from Finnhub.

    Runs in background. Fetches financials, quotes, and calculates valuations.

    Args:
        batch_size: Number of stocks to scrape (default from settings)
        sp500_only: If True, only scrape S&P 500 stocks
        common_stock_only: If True, only scrape Common Stock type (default True)
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

        # Filter to Common Stock only (skip ETFs, ADRs, etc. which don't have SEC filings)
        if common_stock_only:
            query = query.filter(USStock.stock_type == "Common Stock")

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


@router.get("/stats")
def get_us_stocks_stats(db: Session = Depends(get_db)):
    """Get statistics about US stock scraping progress."""
    from sqlalchemy import func, text

    # Total stocks in database
    total_stocks = db.query(func.count(USStock.id)).scalar()

    # Stocks by type
    type_counts = db.execute(text("""
        SELECT stock_type, COUNT(*) as count
        FROM us_stocks
        WHERE stock_type IS NOT NULL
        GROUP BY stock_type
        ORDER BY count DESC
    """)).fetchall()

    # Stocks with financial data
    stocks_with_data = db.execute(text("""
        SELECT COUNT(DISTINCT stock_symbol) FROM us_financial_data
    """)).scalar()

    # Stocks attempted (has last_fundamental_update)
    stocks_attempted = db.query(func.count(USStock.id)).filter(
        USStock.last_fundamental_update.isnot(None)
    ).scalar()

    # Common Stock stats
    common_stock_total = db.query(func.count(USStock.id)).filter(
        USStock.stock_type == "Common Stock"
    ).scalar()

    common_stock_attempted = db.query(func.count(USStock.id)).filter(
        USStock.stock_type == "Common Stock",
        USStock.last_fundamental_update.isnot(None)
    ).scalar()

    common_stock_pending = common_stock_total - common_stock_attempted if common_stock_total else 0

    # S&P 500 stats
    sp500_total = db.query(func.count(USStock.id)).filter(USStock.is_sp500 == True).scalar()
    sp500_with_data = db.execute(text("""
        SELECT COUNT(DISTINCT f.stock_symbol)
        FROM us_financial_data f
        JOIN us_stocks s ON f.stock_symbol = s.symbol
        WHERE s.is_sp500 = true
    """)).scalar()

    # Success rate
    success_rate = round(stocks_with_data / stocks_attempted * 100, 1) if stocks_attempted > 0 else 0

    return {
        "total_stocks_in_db": total_stocks,
        "stocks_with_financial_data": stocks_with_data,
        "stocks_attempted": stocks_attempted,
        "success_rate_pct": success_rate,
        "common_stock": {
            "total": common_stock_total,
            "attempted": common_stock_attempted,
            "pending": common_stock_pending,
        },
        "sp500": {
            "total": sp500_total,
            "with_data": sp500_with_data,
        },
        "by_type": [{"type": row[0], "count": row[1]} for row in type_counts],
    }


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
    from app.stock_data.stock_splits import adjust_eps_for_splits

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
                    value = fin_data[field]
                    # Apply stock split adjustment to EPS
                    if field == "eps" and value is not None:
                        value = adjust_eps_for_splits(symbol, year, value)
                    setattr(existing, field, value)

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

    # ROE - Only calculate if equity is positive
    # Negative equity (from aggressive buybacks) makes ROE meaningless
    if record.net_income and record.total_equity and record.total_equity > 0:
        record.roe = (record.net_income / record.total_equity) * 100
    else:
        # Explicitly set to None for negative equity to avoid misleading values
        record.roe = None

    # ROIC - Return on Invested Capital (works even with negative equity)
    # ROIC = NOPAT / Invested Capital
    # NOPAT = Operating Income * (1 - Tax Rate), estimate 25% tax rate
    # Invested Capital = Total Equity + Total Debt
    if record.operating_income and record.total_debt is not None:
        # Calculate invested capital (equity can be negative, that's fine)
        invested_capital = (record.total_equity or 0) + record.total_debt
        if invested_capital > 0:
            # Estimate NOPAT with 25% tax rate
            nopat = record.operating_income * 0.75
            record.roic = (nopat / invested_capital) * 100
        else:
            record.roic = None
    else:
        record.roic = None

    # ROA
    if record.net_income and record.total_assets and record.total_assets > 0:
        record.roa = (record.net_income / record.total_assets) * 100

    # Debt to Equity - Only meaningful with positive equity
    if record.total_debt is not None and record.total_equity and record.total_equity > 0:
        record.debt_to_equity = record.total_debt / record.total_equity
    else:
        # Negative equity makes D/E ratio meaningless
        record.debt_to_equity = None

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
        big_five_result = big_five_calc.calculate_from_financials(fin_data)
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

            # Calculate 4Ms - extract history arrays from fin_data
            revenue_history = [f.get("revenue") for f in fin_data if f.get("revenue") is not None]
            net_income_history = [f.get("net_income") for f in fin_data if f.get("net_income") is not None]
            roe_history = [f.get("roe") for f in fin_data if f.get("roe") is not None]
            roic_history = [f.get("roic") for f in fin_data if f.get("roic") is not None]
            gross_margin_history = [f.get("gross_margin") for f in fin_data if f.get("gross_margin") is not None]
            operating_margin_history = [f.get("operating_margin") for f in fin_data if f.get("operating_margin") is not None]
            debt_to_equity_history = [f.get("debt_to_equity") for f in fin_data if f.get("debt_to_equity") is not None]
            fcf_history = [f.get("free_cash_flow") for f in fin_data if f.get("free_cash_flow") is not None]

            four_ms_eval = FourMsEvaluator()
            four_ms_result = four_ms_eval.evaluate(
                symbol=symbol,
                revenue_history=revenue_history,
                net_income_history=net_income_history,
                roe_history=roe_history,
                gross_margin_history=gross_margin_history,
                operating_margin_history=operating_margin_history,
                roic_history=roic_history,
                debt_to_equity_history=debt_to_equity_history,
                fcf_history=fcf_history,
                current_price=stock.current_price or 0,
                sticker_price=sticker_result.sticker_price,
                big_five_score=big_five_result.score,
            )

            stock.four_m_score = four_ms_result.overall_score
            stock.four_m_grade = four_ms_result.overall_grade

            # Use Four Ms recommendation (which considers Big Five, MOS, and overall score)
            stock.recommendation = four_ms_result.recommendation

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
    """Determine investment recommendation.

    discount_pct is calculated as: (sticker_price - current_price) / sticker_price * 100
    - Positive = undervalued (price below sticker) = good
    - Negative = overvalued (price above sticker) = bad
    """
    if discount_pct is None:
        return "HOLD"

    # Cap at HOLD if Big Five fails (even if undervalued)
    if big_five_warning:
        if discount_pct >= 50:
            return "HOLD"  # Would be STRONG_BUY but capped due to Big Five
        return "HOLD"

    # Normal recommendation logic
    # Positive discount = undervalued = BUY territory
    # Negative discount = overvalued = SELL territory
    if discount_pct >= 50:
        return "STRONG_BUY"  # 50%+ below sticker price
    elif discount_pct >= 30:
        return "BUY"  # 30-50% below sticker
    elif discount_pct >= -30:
        return "HOLD"  # Within 30% of sticker (either direction)
    elif discount_pct >= -50:
        return "SELL"  # 30-50% above sticker
    else:
        return "STRONG_SELL"  # 50%+ above sticker price


# ============================================================================
# Split Adjustment Fix Endpoint
# ============================================================================

@router.post("/fix-splits")
def fix_stock_splits(
    dry_run: bool = Query(default=True, description="If True, show what would be fixed without making changes"),
    db: Session = Depends(get_db)
):
    """
    Automatically fix EPS values for stock splits.

    This endpoint:
    1. Fetches all stocks with EPS data from the database
    2. Checks yfinance for stock split history
    3. Calculates adjustment factors for historical EPS
    4. Updates the database (if dry_run=False)

    Args:
        dry_run: If True (default), only show what would be fixed. Set to False to apply changes.

    Returns:
        Summary of stocks that need/were fixed
    """
    try:
        from app.services.split_adjustment import apply_split_adjustments

        result = apply_split_adjustments(db, dry_run=dry_run)

        return {
            "status": "success",
            "dry_run": dry_run,
            "message": f"{'Would fix' if dry_run else 'Fixed'} {result['total_records_adjusted']} EPS records across {result['total_stocks_adjusted']} stocks",
            "summary": {
                "total_stocks_adjusted": result["total_stocks_adjusted"],
                "total_records_adjusted": result["total_records_adjusted"],
            },
            "stocks": result["stocks"],
            "note": "Run with dry_run=false to apply changes" if dry_run else "Changes applied successfully"
        }

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"yfinance not installed. Run: pip install yfinance. Error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fixing splits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-splits/{symbol}")
def fix_single_stock_splits(
    symbol: str,
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """Fix EPS values for a single stock's splits."""
    from sqlalchemy import text

    try:
        from app.services.split_adjustment import get_stock_splits, calculate_split_factor

        symbol = symbol.upper()
        splits = get_stock_splits(symbol)

        if not splits:
            return {
                "symbol": symbol,
                "status": "no_splits",
                "message": f"No stock splits found for {symbol}"
            }

        # Get EPS data
        result = db.execute(text("""
            SELECT id, year, eps
            FROM us_financial_data
            WHERE stock_symbol = :symbol AND eps IS NOT NULL
            ORDER BY year
        """), {"symbol": symbol})

        eps_data = [{"id": row[0], "year": row[1], "eps": float(row[2])} for row in result.fetchall()]

        if not eps_data:
            return {
                "symbol": symbol,
                "status": "no_data",
                "message": f"No EPS data found for {symbol}"
            }

        # Calculate adjustments
        adjustments = []
        for record in eps_data:
            factor = calculate_split_factor(splits, record["year"])
            if factor > 1:
                adjustments.append({
                    "id": record["id"],
                    "year": record["year"],
                    "old_eps": record["eps"],
                    "new_eps": round(record["eps"] / factor, 4),
                    "factor": factor
                })

        if not adjustments:
            return {
                "symbol": symbol,
                "status": "no_adjustment_needed",
                "message": f"All EPS data for {symbol} is already adjusted",
                "splits": splits
            }

        # Apply if not dry run
        if not dry_run:
            for adj in adjustments:
                db.execute(text("""
                    UPDATE us_financial_data
                    SET eps = :new_eps, updated_at = NOW()
                    WHERE id = :id
                """), {"new_eps": adj["new_eps"], "id": adj["id"]})
            db.commit()

        return {
            "symbol": symbol,
            "status": "success",
            "dry_run": dry_run,
            "splits": splits,
            "adjustments_count": len(adjustments),
            "adjustments": adjustments,
            "message": f"{'Would fix' if dry_run else 'Fixed'} {len(adjustments)} EPS records"
        }

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"yfinance not installed: {e}")
    except Exception as e:
        logger.error(f"Error fixing splits for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


# ============================================================================
# US Stock Analysis Endpoints (like DSE calculator)
# ============================================================================

@router.get("/{symbol}/big-five")
def get_us_big_five(symbol: str, db: Session = Depends(get_db)):
    """Calculate Big Five Numbers for a US stock."""
    from app.calculations import BigFiveCalculator

    symbol = symbol.upper()

    # Get financial data
    financials = db.query(USFinancialData).filter(
        USFinancialData.stock_symbol == symbol
    ).order_by(USFinancialData.year.asc()).all()

    if len(financials) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient financial data for {symbol}. Try triggering a scrape first."
        )

    # Extract data series (keep all values to maintain year alignment)
    years_list = [f.year for f in financials]
    revenue_history = [f.revenue for f in financials]
    eps_history = [f.eps for f in financials]
    equity_history = [f.total_equity for f in financials]
    ocf_history = [f.operating_cash_flow for f in financials]
    fcf_history = [f.free_cash_flow for f in financials]

    # Calculate
    calculator = BigFiveCalculator()
    result = calculator.calculate(
        revenue_history=revenue_history,
        eps_history=eps_history,
        equity_history=equity_history,
        operating_cf_history=ocf_history,
        free_cf_history=fcf_history,
        years_list=years_list,
    )

    return {
        "symbol": symbol,
        "score": result.score,
        "total": result.total,
        "passes": result.passes,
        "grade": result.grade,
        "revenue": result.revenue.to_dict(),
        "eps": result.eps.to_dict(),
        "equity": result.equity.to_dict(),
        "operating_cf": result.operating_cf.to_dict(),
        "free_cf": result.free_cf.to_dict(),
    }


@router.get("/{symbol}/four-ms")
def get_us_four_ms(symbol: str, db: Session = Depends(get_db)):
    """Calculate 4Ms evaluation for a US stock."""
    from app.calculations import StickerPriceCalculator, BigFiveCalculator, FourMsEvaluator

    symbol = symbol.upper()

    # Get stock record for current price
    stock = db.query(USStock).filter(USStock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"US stock {symbol} not found")

    # Get financial data
    financials = db.query(USFinancialData).filter(
        USFinancialData.stock_symbol == symbol
    ).order_by(USFinancialData.year.asc()).all()

    if len(financials) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient financial data for {symbol}"
        )

    # Extract all data series (keep all values to maintain year alignment for CAGR)
    years_list = [f.year for f in financials]
    revenue_history = [f.revenue for f in financials]
    net_income_history = [f.net_income for f in financials]
    roe_history = [f.roe for f in financials]
    roic_history = [f.roic for f in financials]
    gross_margin_history = [f.gross_margin for f in financials]
    operating_margin_history = [f.operating_margin for f in financials]
    de_history = [f.debt_to_equity for f in financials]
    fcf_history = [f.free_cash_flow for f in financials]
    eps_history = [f.eps for f in financials]

    current_price = stock.current_price or 0

    # Calculate sticker price (filter None for this calculation)
    eps_for_sticker = [e for e in eps_history if e is not None]
    sticker_calc = StickerPriceCalculator()
    sticker_price = 0

    if len(eps_for_sticker) >= 2:
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_for_sticker,
            historical_pe=15.0,  # Default PE for US stocks
        )
        if sticker_result.status == "CALCULABLE":
            sticker_price = sticker_result.sticker_price

    # Calculate Big Five
    big_five_calc = BigFiveCalculator()
    big_five_result = big_five_calc.calculate(
        revenue_history=revenue_history,
        eps_history=eps_history,
        equity_history=[f.total_equity for f in financials],
        operating_cf_history=[f.operating_cash_flow for f in financials],
        free_cf_history=fcf_history,
        years_list=years_list,
    )

    # Calculate 4Ms
    evaluator = FourMsEvaluator()
    result = evaluator.evaluate(
        symbol=symbol,
        revenue_history=revenue_history,
        net_income_history=net_income_history,
        roe_history=roe_history,
        gross_margin_history=gross_margin_history,
        operating_margin_history=operating_margin_history,
        roic_history=roic_history,
        debt_to_equity_history=de_history,
        fcf_history=fcf_history,
        current_price=current_price,
        sticker_price=sticker_price,
        big_five_score=big_five_result.score,
    )

    return result.to_dict()


@router.get("/{symbol}/analysis")
def get_us_full_analysis(symbol: str, db: Session = Depends(get_db)):
    """Get complete Rule #1 analysis for a US stock.

    Combines Sticker Price, Big Five, and 4Ms evaluation.
    """
    from app.calculations import StickerPriceCalculator, BigFiveCalculator, FourMsEvaluator

    symbol = symbol.upper()

    # Get stock record
    stock = db.query(USStock).filter(USStock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"US stock {symbol} not found")

    # Get financial data
    financials = db.query(USFinancialData).filter(
        USFinancialData.stock_symbol == symbol
    ).order_by(USFinancialData.year.asc()).all()

    if len(financials) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient financial data for {symbol}. Trigger a scrape first."
        )

    current_price = stock.current_price

    # Extract data series (keep all values to maintain year alignment for CAGR)
    years_list = [f.year for f in financials]
    eps_history = [f.eps for f in financials]
    revenue_history = [f.revenue for f in financials]
    net_income_history = [f.net_income for f in financials]
    roe_history = [f.roe for f in financials]
    roic_history = [f.roic for f in financials]
    gross_margin_history = [f.gross_margin for f in financials]
    operating_margin_history = [f.operating_margin for f in financials]
    de_history = [f.debt_to_equity for f in financials]
    fcf_history = [f.free_cash_flow for f in financials]
    equity_history = [f.total_equity for f in financials]
    ocf_history = [f.operating_cash_flow for f in financials]

    # Calculate Sticker Price (filter None for this calculation)
    eps_for_sticker = [e for e in eps_history if e is not None]
    sticker_calc = StickerPriceCalculator()
    sticker_result = None
    if len(eps_for_sticker) >= 2:
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_for_sticker,
            historical_pe=15.0,
            current_price=current_price,
        )

    # Calculate Big Five
    big_five_calc = BigFiveCalculator()
    big_five_result = big_five_calc.calculate(
        revenue_history=revenue_history,
        eps_history=eps_history,
        equity_history=equity_history,
        operating_cf_history=ocf_history,
        free_cf_history=fcf_history,
        years_list=years_list,
    )

    # Calculate 4Ms
    evaluator = FourMsEvaluator()
    four_ms_result = evaluator.evaluate(
        symbol=symbol,
        revenue_history=revenue_history,
        net_income_history=net_income_history,
        roe_history=roe_history,
        gross_margin_history=gross_margin_history,
        operating_margin_history=operating_margin_history,
        roic_history=roic_history,
        debt_to_equity_history=de_history,
        fcf_history=fcf_history,
        current_price=current_price or 0,
        sticker_price=sticker_result.sticker_price if sticker_result and sticker_result.status == "CALCULABLE" else 0,
        big_five_score=big_five_result.score,
    )

    return {
        "symbol": symbol,
        "name": stock.name,
        "sector": stock.sector,
        "is_sp500": stock.is_sp500,
        "current_price": current_price,
        "sticker_price": sticker_result.to_dict() if sticker_result else None,
        "big_five": big_five_result.to_dict(),
        "four_ms": four_ms_result.to_dict(),
        "data_years": len(financials),
        "recommendation": four_ms_result.recommendation,
    }
