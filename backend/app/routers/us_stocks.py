"""US Stock data API endpoints.

Financial data comes from SimFin bulk import.
Finnhub is only used for live quotes and symbol seeding.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio
import logging
import pandas as pd

from app.database import get_db
from app.models.us_stock import USStock, USFinancialData
from app.config import get_settings

logger = logging.getLogger(__name__)

# Global state for tracking seed progress
_seed_progress: Dict[str, Any] = {
    "running": False,
    "fetched": 0,
    "inserted": 0,
    "updated_types": 0,
    "started_at": None,
    "completed_at": None,
}

# Global state for tracking valuation calculation progress
_valuation_progress: Dict[str, Any] = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_symbol": "",
    "success_count": 0,
    "failed_count": 0,
    "started_at": None,
}

# Global state for tracking SimFin import progress
_simfin_progress: Dict[str, Any] = {
    "running": False,
    "stage": "",
    "records_processed": 0,
    "records_total": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
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
    current_liabilities: Optional[int] = None
    total_debt: Optional[int] = None
    operating_cash_flow: Optional[int] = None
    capital_expenditure: Optional[int] = None
    free_cash_flow: Optional[int] = None
    roe: Optional[float] = None
    roic: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None


class SeedRequest(BaseModel):
    sp500_only: bool = False


# ============================================================================
# API Endpoints - Read Data
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
        sort_by: Column to sort by
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
    """Get counts for all filter categories in one request."""
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
            detail=f"No financial data found for {symbol}. Run SimFin import first."
        )

    return {
        "symbol": symbol.upper(),
        "source": "simfin",
        "data": [
            USFinancialRecord(
                year=f.year,
                revenue=f.revenue,
                net_income=f.net_income,
                eps=f.eps,
                total_equity=f.total_equity,
                total_assets=f.total_assets,
                current_liabilities=f.current_liabilities,
                total_debt=f.total_debt,
                operating_cash_flow=f.operating_cash_flow,
                capital_expenditure=f.capital_expenditure,
                free_cash_flow=f.free_cash_flow,
                roe=f.roe,
                roic=f.roic,
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
# Seed Endpoints - Populate stock symbols from Finnhub
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

            # Update existing stocks that don't have stock_type set
            updated_types = 0
            stocks_without_type = db.query(USStock.id, USStock.symbol).filter(USStock.stock_type.is_(None)).all()

            batch_size = 1000
            update_batch = []
            for stock_id, symbol in stocks_without_type:
                if symbol in symbol_type_map:
                    update_batch.append({"id": stock_id, "stock_type": symbol_type_map[symbol]})
                    updated_types += 1

                if len(update_batch) >= batch_size:
                    db.bulk_update_mappings(USStock, update_batch)
                    db.commit()
                    _seed_progress["updated_types"] = updated_types
                    update_batch = []

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


# ============================================================================
# SimFin Import Endpoint
# ============================================================================

async def _run_simfin_import_background():
    """Background task to import SimFin data."""
    global _simfin_progress
    from app.database import SessionLocal

    _simfin_progress["running"] = True
    _simfin_progress["started_at"] = datetime.now().isoformat()
    _simfin_progress["completed_at"] = None
    _simfin_progress["error"] = None
    _simfin_progress["stage"] = "starting"

    try:
        from app.services.simfin_import import (
            setup_simfin, download_all_datasets, merge_financial_data,
            prepare_for_database, import_to_database
        )

        # Setup
        _simfin_progress["stage"] = "setup"
        setup_simfin()

        # Download datasets
        _simfin_progress["stage"] = "downloading"
        datasets = download_all_datasets()

        # Merge data
        _simfin_progress["stage"] = "merging"
        merged_df = merge_financial_data(datasets)

        # Prepare records
        _simfin_progress["stage"] = "preparing"
        records = prepare_for_database(merged_df)
        _simfin_progress["records_total"] = len(records)

        # Import to database
        _simfin_progress["stage"] = "importing"
        imported, updated = import_to_database(records)
        _simfin_progress["records_processed"] = imported + updated

        _simfin_progress["stage"] = "complete"
        logger.info(f"SimFin import complete: {imported} new, {updated} updated")

    except Exception as e:
        logger.error(f"SimFin import failed: {e}")
        _simfin_progress["error"] = str(e)
        _simfin_progress["stage"] = "failed"

    finally:
        _simfin_progress["running"] = False
        _simfin_progress["completed_at"] = datetime.now().isoformat()


@router.post("/import-simfin")
async def import_simfin_data(background_tasks: BackgroundTasks):
    """Import financial data from SimFin.

    Downloads bulk financial data (income, balance sheet, cash flow)
    and imports it to the us_financial_data table.

    Runs in background due to large data volume (~50k+ records).
    """
    global _simfin_progress

    if _simfin_progress["running"]:
        return {
            "status": "already_running",
            "message": "SimFin import already in progress",
            "progress": _simfin_progress,
        }

    background_tasks.add_task(_run_simfin_import_background)

    return {
        "status": "started",
        "message": "SimFin import started in background",
        "check_progress_at": "/us-stocks/simfin-status",
    }


@router.get("/simfin-status")
async def get_simfin_status():
    """Get the status of SimFin import."""
    return _simfin_progress


# ============================================================================
# EPS/ROIC Update Endpoint (faster than full re-import)
# ============================================================================

_eps_update_progress = {
    "running": False,
    "current": 0,
    "total": 0,
    "updated_count": 0,
}


async def _run_eps_update():
    """Background task to update EPS and ROIC from SimFin derived dataset."""
    global _eps_update_progress
    import simfin as sf
    import os
    from app.database import SessionLocal

    _eps_update_progress["running"] = True
    _eps_update_progress["current"] = 0
    _eps_update_progress["updated_count"] = 0

    try:
        # Setup SimFin
        api_key = os.getenv("SIMFIN_API_KEY", "83a17c9a-cd93-47c8-b47e-bec3e4cd23c2")
        data_dir = os.path.join(os.path.dirname(__file__), "../../simfin_data")
        sf.set_api_key(api_key)
        sf.set_data_dir(data_dir)
        os.makedirs(data_dir, exist_ok=True)

        logger.info("Loading SimFin derived dataset for EPS/ROIC...")
        derived = sf.load_derived(variant='annual', market='us', refresh_days=0)
        derived = derived.reset_index()

        _eps_update_progress["total"] = len(derived)
        logger.info(f"Loaded {len(derived)} derived records")

        # Process in batches
        db = SessionLocal()
        batch_size = 100
        updated = 0

        for i in range(0, len(derived), batch_size):
            batch = derived.iloc[i:i+batch_size]

            for _, row in batch.iterrows():
                symbol = row.get('Ticker')
                year = int(row.get('Fiscal Year'))
                eps = row.get('Earnings Per Share, Diluted')
                roic = row.get('Return On Invested Capital')

                if pd.isna(symbol) or pd.isna(year):
                    continue

                # Update record
                update_fields = {}
                if not pd.isna(eps):
                    update_fields['eps'] = float(eps)
                if not pd.isna(roic):
                    update_fields['roic'] = float(roic) * 100  # Convert to percentage

                if update_fields:
                    result = db.execute(
                        text("""
                            UPDATE us_financial_data
                            SET eps = COALESCE(:eps, eps),
                                roic = COALESCE(:roic, roic)
                            WHERE stock_symbol = :symbol AND year = :year
                        """),
                        {
                            "eps": update_fields.get('eps'),
                            "roic": update_fields.get('roic'),
                            "symbol": symbol,
                            "year": year
                        }
                    )
                    if result.rowcount > 0:
                        updated += 1

            db.commit()
            _eps_update_progress["current"] = min(i + batch_size, len(derived))
            _eps_update_progress["updated_count"] = updated

            if i % 5000 == 0:
                logger.info(f"EPS update progress: {i}/{len(derived)} ({updated} updated)")

        logger.info(f"EPS/ROIC update complete: {updated} records updated")

    except Exception as e:
        logger.error(f"EPS update failed: {e}")
        raise
    finally:
        _eps_update_progress["running"] = False
        db.close()


@router.post("/update-eps")
async def update_eps_roic(background_tasks: BackgroundTasks):
    """Update only EPS and ROIC from SimFin derived dataset.

    Faster than full re-import - only updates these two fields.
    """
    global _eps_update_progress

    if _eps_update_progress["running"]:
        return {
            "status": "already_running",
            "progress": _eps_update_progress
        }

    background_tasks.add_task(_run_eps_update)

    return {
        "status": "started",
        "message": "EPS/ROIC update started",
        "check_progress_at": "/us-stocks/eps-update-status"
    }


@router.get("/eps-update-status")
async def get_eps_update_status():
    """Get status of EPS/ROIC update."""
    return _eps_update_progress


# ============================================================================
# Valuation Calculation Endpoint
# ============================================================================

async def _run_valuation_calculation(symbols: List[str]):
    """Background task to calculate valuations for stocks."""
    global _valuation_progress
    from app.database import SessionLocal

    _valuation_progress["running"] = True
    _valuation_progress["current"] = 0
    _valuation_progress["total"] = len(symbols)
    _valuation_progress["success_count"] = 0
    _valuation_progress["failed_count"] = 0
    _valuation_progress["started_at"] = datetime.now().isoformat()

    db = SessionLocal()

    try:
        for i, symbol in enumerate(symbols):
            if not _valuation_progress["running"]:
                logger.info("Valuation calculation stopped by user")
                break

            _valuation_progress["current_symbol"] = symbol

            try:
                _calculate_us_valuations(db, symbol)
                _valuation_progress["success_count"] += 1
            except Exception as e:
                logger.error(f"Error calculating valuations for {symbol}: {e}")
                _valuation_progress["failed_count"] += 1

            _valuation_progress["current"] = i + 1

            # Small delay to prevent overload
            if i < len(symbols) - 1:
                await asyncio.sleep(0.1)

    finally:
        _valuation_progress["running"] = False
        db.close()


@router.post("/calculate-valuations")
async def calculate_valuations(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(default=1000),
    symbol: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Calculate Phil Town valuations for stocks with financial data.

    This recalculates sticker price, Big Five, and 4Ms scores
    based on existing financial data in the database.

    Args:
        batch_size: Number of stocks to process
        symbol: If provided, only calculate for this symbol
    """
    global _valuation_progress

    if _valuation_progress["running"]:
        return {
            "status": "already_running",
            "message": "Valuation calculation already in progress",
            "progress": {
                "current": _valuation_progress["current"],
                "total": _valuation_progress["total"],
                "current_symbol": _valuation_progress["current_symbol"],
            }
        }

    # Get stocks to calculate
    if symbol:
        symbols = [symbol.upper()]
    else:
        # Get symbols that have financial data
        result = db.execute(text("""
            SELECT DISTINCT s.symbol
            FROM us_stocks s
            JOIN us_financial_data f ON s.symbol = f.stock_symbol
            WHERE s.stock_type = 'Common Stock'
            ORDER BY s.symbol
            LIMIT :limit
        """), {"limit": batch_size})
        symbols = [row[0] for row in result.fetchall()]

    if not symbols:
        raise HTTPException(
            status_code=400,
            detail="No stocks with financial data found. Run SimFin import first."
        )

    background_tasks.add_task(_run_valuation_calculation, symbols)

    return {
        "status": "started",
        "message": f"Started calculating valuations for {len(symbols)} stocks",
        "total_stocks": len(symbols),
        "check_progress_at": "/us-stocks/valuation-status",
    }


@router.get("/valuation-status")
def get_valuation_status():
    """Get current status of valuation calculation."""
    global _valuation_progress

    progress_percent = None
    if _valuation_progress["total"] > 0:
        progress_percent = round(
            _valuation_progress["current"] / _valuation_progress["total"] * 100, 1
        )

    return {
        "running": _valuation_progress["running"],
        "current": _valuation_progress["current"],
        "total": _valuation_progress["total"],
        "current_symbol": _valuation_progress["current_symbol"],
        "success_count": _valuation_progress["success_count"],
        "failed_count": _valuation_progress["failed_count"],
        "progress_percent": progress_percent,
        "started_at": _valuation_progress["started_at"],
    }


@router.post("/stop-calculations")
def stop_calculations():
    """Stop the running valuation calculations."""
    global _valuation_progress

    if not _valuation_progress["running"]:
        return {"status": "not_running", "message": "No calculation is running"}

    _valuation_progress["running"] = False

    return {
        "status": "stopping",
        "message": "Calculations will stop after current stock completes",
        "calculated_so_far": _valuation_progress["current"],
    }


# ============================================================================
# Stats Endpoint
# ============================================================================

@router.get("/stats")
def get_us_stocks_stats(db: Session = Depends(get_db)):
    """Get statistics about US stock data."""
    from sqlalchemy import func

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

    # Stocks with valuations
    stocks_with_valuations = db.query(func.count(USStock.id)).filter(
        USStock.valuation_status == "CALCULABLE"
    ).scalar()

    # Common Stock stats
    common_stock_total = db.query(func.count(USStock.id)).filter(
        USStock.stock_type == "Common Stock"
    ).scalar()

    # S&P 500 stats
    sp500_total = db.query(func.count(USStock.id)).filter(USStock.is_sp500 == True).scalar()
    sp500_with_data = db.execute(text("""
        SELECT COUNT(DISTINCT f.stock_symbol)
        FROM us_financial_data f
        JOIN us_stocks s ON f.stock_symbol = s.symbol
        WHERE s.is_sp500 = true
    """)).scalar()

    return {
        "total_stocks_in_db": total_stocks,
        "stocks_with_financial_data": stocks_with_data,
        "stocks_with_valuations": stocks_with_valuations,
        "common_stock": {
            "total": common_stock_total,
        },
        "sp500": {
            "total": sp500_total,
            "with_data": sp500_with_data,
        },
        "by_type": [{"type": row[0], "count": row[1]} for row in type_counts],
    }


# ============================================================================
# Valuation Calculation Function
# ============================================================================

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
                "roic": f.roic,
                "debt_to_equity": f.debt_to_equity,
                "gross_margin": f.gross_margin,
                "operating_margin": f.operating_margin,
                "net_income": f.net_income,
            })

        # Extract history arrays
        years_list = [f.year for f in financials]
        eps_history = [f.eps for f in financials]
        revenue_history = [f.revenue for f in financials]
        equity_history = [f.total_equity for f in financials]
        ocf_history = [f.operating_cash_flow for f in financials]
        fcf_history = [f.free_cash_flow for f in financials]

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
        stock.big_five_score = big_five_result.score
        stock.big_five_warning = not big_five_result.passes

        # Calculate Sticker Price
        eps_for_sticker = [e for e in eps_history if e is not None]
        if len(eps_for_sticker) < 2:
            stock.valuation_status = "NOT_CALCULABLE"
            stock.valuation_note = "Missing EPS data for sticker price calculation"
            db.commit()
            return

        pe_avg = 15.0  # Default PE
        sticker_calc = StickerPriceCalculator()
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_for_sticker,
            historical_pe=pe_avg,
            current_price=stock.current_price
        )

        if sticker_result.status == "CALCULABLE":
            stock.sticker_price = sticker_result.sticker_price
            stock.margin_of_safety = sticker_result.margin_of_safety
            stock.discount_to_sticker = sticker_result.discount_to_sticker

            # Calculate 4Ms
            net_income_history = [f.get("net_income") for f in fin_data]
            roe_history = [f.get("roe") for f in fin_data]
            roic_history = [f.get("roic") for f in fin_data]
            gross_margin_history = [f.get("gross_margin") for f in fin_data]
            operating_margin_history = [f.get("operating_margin") for f in fin_data]
            debt_to_equity_history = [f.get("debt_to_equity") for f in fin_data]

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
                equity_history=equity_history,
                current_price=stock.current_price or 0,
                sticker_price=sticker_result.sticker_price,
                big_five_score=big_five_result.score,
            )

            stock.four_m_score = four_ms_result.overall_score
            stock.four_m_grade = four_ms_result.overall_grade
            stock.recommendation = four_ms_result.recommendation

            stock.valuation_status = "CALCULABLE"
            stock.valuation_note = None
        else:
            stock.valuation_status = "NOT_CALCULABLE"
            stock.valuation_note = sticker_result.note or "Could not calculate sticker price"

        stock.last_valuation_update = datetime.now()
        stock.last_fundamental_update = datetime.now()
        db.commit()

    except Exception as e:
        logger.error(f"Error calculating valuations for {symbol}: {e}")
        stock.valuation_status = "NOT_CALCULABLE"
        stock.valuation_note = f"Calculation error: {str(e)}"
        db.commit()


# ============================================================================
# Single Stock Route (MUST be at end to avoid matching other routes)
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
# US Stock Analysis Endpoints
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
            detail=f"Insufficient financial data for {symbol}. Run SimFin import first."
        )

    # Extract data series
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

    # Extract all data series
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
    equity_history = [f.total_equity for f in financials]
    ocf_history = [f.operating_cash_flow for f in financials]

    current_price = stock.current_price or 0

    # Calculate sticker price
    eps_for_sticker = [e for e in eps_history if e is not None]
    sticker_calc = StickerPriceCalculator()
    sticker_price = 0

    if len(eps_for_sticker) >= 2:
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_for_sticker,
            historical_pe=15.0,
        )
        if sticker_result.status == "CALCULABLE":
            sticker_price = sticker_result.sticker_price

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
        equity_history=equity_history,
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
            detail=f"Insufficient financial data for {symbol}. Run SimFin import first."
        )

    current_price = stock.current_price

    # Extract data series
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

    # Calculate Sticker Price
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
        equity_history=equity_history,
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
