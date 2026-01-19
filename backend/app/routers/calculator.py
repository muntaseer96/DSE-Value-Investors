"""Calculator API endpoints - Sticker Price, Big Five, 4Ms."""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_db
from app.models import Stock, FinancialData
from app.services import DSEDataService
from app.calculations import StickerPriceCalculator, BigFiveCalculator, FourMsEvaluator

logger = logging.getLogger(__name__)

# Global state for tracking valuation refresh progress
_valuation_progress: Dict[str, Any] = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_symbol": "",
    "success_count": 0,
    "failed_count": 0,
    "started_at": None,
    "completed_at": None,
}

router = APIRouter(prefix="/calculate", tags=["Calculator"])


class StickerPriceRequest(BaseModel):
    symbol: Optional[str] = None
    current_eps: Optional[float] = None
    eps_growth_rate: Optional[float] = None  # As percentage, e.g., 12 for 12%
    historical_pe: Optional[float] = None
    current_price: Optional[float] = None


class StickerPriceResponse(BaseModel):
    symbol: Optional[str] = None
    current_eps: float
    eps_growth_rate: float
    used_growth_rate: float
    historical_pe: float
    future_eps: float
    future_pe: float
    future_price: float
    sticker_price: float
    margin_of_safety: float
    current_price: Optional[float] = None
    discount_to_sticker: Optional[float] = None
    discount_to_mos: Optional[float] = None
    recommendation: Optional[str] = None
    status: str = "CALCULABLE"  # CALCULABLE, NOT_CALCULABLE
    note: Optional[str] = None  # Explanation when not calculable


class BigFiveResponse(BaseModel):
    symbol: str
    score: int
    total: int
    passes: bool
    grade: str
    revenue: dict
    eps: dict
    equity: dict
    operating_cf: dict
    free_cf: dict


@router.post("/sticker-price", response_model=StickerPriceResponse)
def calculate_sticker_price(request: StickerPriceRequest, db: Session = Depends(get_db)):
    """Calculate Sticker Price for a stock.

    You can either:
    1. Provide a symbol - we'll fetch the data automatically
    2. Provide manual values (current_eps, eps_growth_rate, historical_pe)
    """
    calculator = StickerPriceCalculator()

    if request.symbol:
        # Fetch data automatically
        financials = db.query(FinancialData).filter(
            FinancialData.stock_symbol == request.symbol.upper()
        ).order_by(FinancialData.year.asc()).all()

        if len(financials) < 2:
            # Try to fetch from external source
            data_service = DSEDataService()
            raw_data = data_service.get_fundamental_data(request.symbol.upper())

            if raw_data.get("success"):
                parsed = data_service.parse_financial_data(raw_data)
                # Save to database
                for record in parsed:
                    existing = db.query(FinancialData).filter(
                        FinancialData.stock_symbol == request.symbol.upper(),
                        FinancialData.year == record["year"]
                    ).first()
                    if not existing:
                        db.add(FinancialData(
                            stock_symbol=request.symbol.upper(),
                            source="stocksurferbd",
                            **record
                        ))
                db.commit()

                # Query again
                financials = db.query(FinancialData).filter(
                    FinancialData.stock_symbol == request.symbol.upper()
                ).order_by(FinancialData.year.asc()).all()

        if len(financials) < 2:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient financial data for {request.symbol}. Need at least 2 years of data."
            )

        # Extract EPS history (include all values, even None/negative for quality check)
        eps_history = [f.eps for f in financials if f.eps is not None]

        # Get historical PE (average from data or use default)
        pe_values = [f.pe_ratio for f in financials if f.pe_ratio]
        historical_pe = sum(pe_values) / len(pe_values) if pe_values else 15.0

        # Get current price if not provided
        current_price = request.current_price
        if current_price is None:
            data_service = DSEDataService()
            price_data = data_service.get_stock_price(request.symbol.upper())
            if price_data:
                current_price = float(price_data.get('ltp', price_data.get('close', 0)))

        # Use calculate_from_financials which includes quality check
        result = calculator.calculate_from_financials(
            eps_history=eps_history,
            historical_pe=historical_pe,
            current_price=current_price,
        )

    else:
        # Use manual values
        if request.current_eps is None or request.eps_growth_rate is None or request.historical_pe is None:
            raise HTTPException(
                status_code=400,
                detail="Must provide either symbol or (current_eps, eps_growth_rate, historical_pe)"
            )

        current_eps = request.current_eps
        eps_growth_rate = request.eps_growth_rate / 100  # Convert from percentage
        historical_pe = request.historical_pe
        current_price = request.current_price

        # For manual input, use direct calculate (user knows what they're doing)
        result = calculator.calculate(
            current_eps=current_eps,
            eps_growth_rate=eps_growth_rate,
            historical_pe=historical_pe,
            current_price=current_price,
        )

    return StickerPriceResponse(
        symbol=request.symbol.upper() if request.symbol else None,
        **result.to_dict()
    )


@router.get("/sticker-price/{symbol}", response_model=StickerPriceResponse)
def get_sticker_price(symbol: str, db: Session = Depends(get_db)):
    """Get Sticker Price for a stock by symbol."""
    return calculate_sticker_price(StickerPriceRequest(symbol=symbol), db)


@router.get("/big-five/{symbol}", response_model=BigFiveResponse)
def calculate_big_five(symbol: str, db: Session = Depends(get_db)):
    """Calculate Big Five Numbers for a stock."""
    # Get financial data
    financials = db.query(FinancialData).filter(
        FinancialData.stock_symbol == symbol.upper()
    ).order_by(FinancialData.year.asc()).all()

    if len(financials) < 2:
        # Try to fetch
        data_service = DSEDataService()
        raw_data = data_service.get_fundamental_data(symbol.upper())

        if raw_data.get("success"):
            parsed = data_service.parse_financial_data(raw_data)
            for record in parsed:
                existing = db.query(FinancialData).filter(
                    FinancialData.stock_symbol == symbol.upper(),
                    FinancialData.year == record["year"]
                ).first()
                if not existing:
                    db.add(FinancialData(
                        stock_symbol=symbol.upper(),
                        source="stocksurferbd",
                        **record
                    ))
            db.commit()
            financials = db.query(FinancialData).filter(
                FinancialData.stock_symbol == symbol.upper()
            ).order_by(FinancialData.year.asc()).all()

    if len(financials) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient financial data for {symbol}"
        )

    # Extract data series
    revenue_history = [f.revenue for f in financials if f.revenue]
    eps_history = [f.eps for f in financials if f.eps]
    equity_history = [f.total_equity for f in financials if f.total_equity]
    ocf_history = [f.operating_cash_flow for f in financials if f.operating_cash_flow]
    fcf_history = [f.free_cash_flow for f in financials if f.free_cash_flow]

    # Calculate
    calculator = BigFiveCalculator()
    result = calculator.calculate(
        revenue_history=revenue_history,
        eps_history=eps_history,
        equity_history=equity_history,
        operating_cf_history=ocf_history,
        free_cf_history=fcf_history,
    )

    return BigFiveResponse(
        symbol=symbol.upper(),
        score=result.score,
        total=result.total,
        passes=result.passes,
        grade=result.grade,
        revenue=result.revenue.to_dict(),
        eps=result.eps.to_dict(),
        equity=result.equity.to_dict(),
        operating_cf=result.operating_cf.to_dict(),
        free_cf=result.free_cf.to_dict(),
    )


@router.get("/four-ms/{symbol}")
def calculate_four_ms(symbol: str, db: Session = Depends(get_db)):
    """Calculate 4Ms evaluation for a stock - 100% objective from financial data.

    No user inputs required. All scores are calculated from:
    - Meaning: Revenue stability, earnings consistency, dividends, data quality
    - Moat: ROE, gross margins, operating margins
    - Management: ROE consistency, debt levels, FCF generation, dividends
    - MOS: Current price vs sticker price
    """
    symbol = symbol.upper()

    # Get financial data
    financials = db.query(FinancialData).filter(
        FinancialData.stock_symbol == symbol
    ).order_by(FinancialData.year.asc()).all()

    if len(financials) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient financial data for {symbol}. Run /stocks/{symbol}/fundamentals first."
        )

    # Extract all data series for objective evaluation
    revenue_history = [f.revenue for f in financials if f.revenue]
    net_income_history = [f.net_income for f in financials if f.net_income]
    roe_history = [f.roe for f in financials if f.roe]
    gross_margin_history = [f.gross_margin for f in financials if f.gross_margin]
    operating_margin_history = [f.operating_margin for f in financials if f.operating_margin]
    de_history = [f.debt_to_equity for f in financials if f.debt_to_equity is not None]
    fcf_history = [f.free_cash_flow for f in financials if f.free_cash_flow]
    eps_history = [f.eps for f in financials if f.eps is not None]

    # Get current price
    data_service = DSEDataService()
    price_data = data_service.get_stock_price(symbol)
    current_price = float(price_data.get('ltp', price_data.get('close', 0))) if price_data else 0

    # Calculate sticker price (with quality check)
    sticker_calc = StickerPriceCalculator()
    sticker_price = 0

    if len(eps_history) >= 2:
        pe_values = [f.pe_ratio for f in financials if f.pe_ratio]
        historical_pe = sum(pe_values) / len(pe_values) if pe_values else 15.0
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_history,
            historical_pe=historical_pe,
        )
        # Only use sticker price if calculable
        if sticker_result.status == "CALCULABLE":
            sticker_price = sticker_result.sticker_price

    # Calculate 4Ms - fully objective
    evaluator = FourMsEvaluator()
    result = evaluator.evaluate(
        symbol=symbol,
        revenue_history=revenue_history,
        net_income_history=net_income_history,
        roe_history=roe_history,
        gross_margin_history=gross_margin_history,
        operating_margin_history=operating_margin_history,
        debt_to_equity_history=de_history,
        fcf_history=fcf_history,
        current_price=current_price,
        sticker_price=sticker_price,
    )

    return result.to_dict()


@router.get("/analysis/{symbol}")
def get_full_analysis(symbol: str, db: Session = Depends(get_db)):
    """Get complete Rule #1 analysis for a stock.

    Combines Sticker Price, Big Five, and basic 4Ms evaluation.
    """
    symbol = symbol.upper()

    # Try to get/fetch fundamentals first
    data_service = DSEDataService()

    financials = db.query(FinancialData).filter(
        FinancialData.stock_symbol == symbol
    ).order_by(FinancialData.year.asc()).all()

    if len(financials) < 2:
        # Fetch fundamentals
        raw_data = data_service.get_fundamental_data(symbol)
        if raw_data.get("success"):
            parsed = data_service.parse_financial_data(raw_data)
            for record in parsed:
                existing = db.query(FinancialData).filter(
                    FinancialData.stock_symbol == symbol,
                    FinancialData.year == record["year"]
                ).first()
                if not existing:
                    db.add(FinancialData(
                        stock_symbol=symbol,
                        source="stocksurferbd",
                        **record
                    ))
            db.commit()
            financials = db.query(FinancialData).filter(
                FinancialData.stock_symbol == symbol
            ).order_by(FinancialData.year.asc()).all()

    if len(financials) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch sufficient data for {symbol}"
        )

    # Get current price
    price_data = data_service.get_stock_price(symbol)
    current_price = None
    if price_data:
        current_price = float(price_data.get('ltp', price_data.get('close', 0))) or None

    # Calculate Sticker Price (include all EPS values for quality check)
    eps_history = [f.eps for f in financials if f.eps is not None]
    sticker_calc = StickerPriceCalculator()

    sticker_result = None
    if len(eps_history) >= 2:
        pe_values = [f.pe_ratio for f in financials if f.pe_ratio]
        historical_pe = sum(pe_values) / len(pe_values) if pe_values else 15.0
        # Use calculate_from_financials which includes quality check
        sticker_result = sticker_calc.calculate_from_financials(
            eps_history=eps_history,
            historical_pe=historical_pe,
            current_price=current_price,
        )

    # Calculate Big Five
    big_five_calc = BigFiveCalculator()
    big_five_result = big_five_calc.calculate(
        revenue_history=[f.revenue for f in financials if f.revenue],
        eps_history=eps_history,
        equity_history=[f.total_equity for f in financials if f.total_equity],
        operating_cf_history=[f.operating_cash_flow for f in financials if f.operating_cash_flow],
        free_cf_history=[f.free_cash_flow for f in financials if f.free_cash_flow],
    )

    # Calculate 4Ms - fully objective
    evaluator = FourMsEvaluator()
    four_ms_result = evaluator.evaluate(
        symbol=symbol,
        revenue_history=[f.revenue for f in financials if f.revenue],
        net_income_history=[f.net_income for f in financials if f.net_income],
        roe_history=[f.roe for f in financials if f.roe],
        gross_margin_history=[f.gross_margin for f in financials if f.gross_margin],
        operating_margin_history=[f.operating_margin for f in financials if f.operating_margin],
        debt_to_equity_history=[f.debt_to_equity for f in financials if f.debt_to_equity is not None],
        fcf_history=[f.free_cash_flow for f in financials if f.free_cash_flow],
        current_price=current_price or 0,
        sticker_price=sticker_result.sticker_price if sticker_result else 0,
    )

    return {
        "symbol": symbol,
        "current_price": current_price,
        "sticker_price": sticker_result.to_dict() if sticker_result else None,
        "big_five": big_five_result.to_dict(),
        "four_ms": four_ms_result.to_dict(),
        "data_years": len(financials),
        "recommendation": sticker_result.recommendation if sticker_result else four_ms_result.recommendation,
    }


# ============================================================================
# Batch Valuation Endpoints
# ============================================================================

class BatchValuationItem(BaseModel):
    """Response model for a single stock's valuation."""
    symbol: str
    sticker_price: Optional[float] = None
    margin_of_safety: Optional[float] = None
    four_m_score: Optional[float] = None
    four_m_grade: Optional[str] = None
    recommendation: Optional[str] = None
    discount_to_sticker: Optional[float] = None
    valuation_status: str = "UNKNOWN"
    valuation_note: Optional[str] = None
    last_valuation_update: Optional[str] = None


class BatchValuationsResponse(BaseModel):
    """Response model for batch valuations."""
    count: int
    calculable_count: int
    not_calculable_count: int
    last_refresh: Optional[str] = None
    valuations: List[BatchValuationItem]


@router.get("/batch-valuations", response_model=BatchValuationsResponse)
def get_batch_valuations(db: Session = Depends(get_db)):
    """Get all pre-calculated valuations from cache (stocks table).

    Returns valuations for all stocks that have been calculated.
    Fast read from database - no calculations performed.
    """
    # Get all stocks with valuations
    stocks_with_vals = db.query(Stock).filter(
        Stock.valuation_status.in_(["CALCULABLE", "NOT_CALCULABLE"])
    ).all()

    valuations = []
    calculable_count = 0
    not_calculable_count = 0
    latest_update = None

    for stock in stocks_with_vals:
        if stock.valuation_status == "CALCULABLE":
            calculable_count += 1
        else:
            not_calculable_count += 1

        if stock.last_valuation_update:
            if latest_update is None or stock.last_valuation_update > latest_update:
                latest_update = stock.last_valuation_update

        valuations.append(BatchValuationItem(
            symbol=stock.symbol,
            sticker_price=stock.sticker_price,
            margin_of_safety=stock.margin_of_safety,
            four_m_score=stock.four_m_score,
            four_m_grade=stock.four_m_grade,
            recommendation=stock.recommendation,
            discount_to_sticker=stock.discount_to_sticker,
            valuation_status=stock.valuation_status or "UNKNOWN",
            valuation_note=stock.valuation_note,
            last_valuation_update=stock.last_valuation_update.isoformat() if stock.last_valuation_update else None,
        ))

    return BatchValuationsResponse(
        count=len(valuations),
        calculable_count=calculable_count,
        not_calculable_count=not_calculable_count,
        last_refresh=latest_update.isoformat() if latest_update else None,
        valuations=valuations,
    )


@router.post("/refresh-valuations")
def refresh_valuations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start background refresh of all stock valuations.

    Re-calculates sticker price, 4Ms for all stocks with financial data
    and updates the stocks table cache.

    Use GET /calculate/refresh-valuations-status to check progress.
    """
    global _valuation_progress

    if _valuation_progress["running"]:
        return {
            "status": "already_running",
            "message": "Valuation refresh already in progress",
            "progress": {
                "current": _valuation_progress["current"],
                "total": _valuation_progress["total"],
                "current_symbol": _valuation_progress["current_symbol"],
            }
        }

    # Get all unique symbols from financial_data
    symbols_query = db.query(FinancialData.stock_symbol).distinct().all()
    symbols = [s[0] for s in symbols_query if s[0]]

    if not symbols:
        raise HTTPException(
            status_code=400,
            detail="No financial data found. Run fundamentals scrape first."
        )

    # Reset progress
    _valuation_progress = {
        "running": True,
        "current": 0,
        "total": len(symbols),
        "current_symbol": "",
        "success_count": 0,
        "failed_count": 0,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    # Start background task
    background_tasks.add_task(_run_valuation_refresh, symbols)

    return {
        "status": "started",
        "message": f"Started refreshing valuations for {len(symbols)} stocks",
        "total_stocks": len(symbols),
        "check_progress_at": "/calculate/refresh-valuations-status"
    }


@router.get("/refresh-valuations-status")
def get_refresh_status():
    """Get current status of valuation refresh operation."""
    global _valuation_progress

    response = {
        "running": _valuation_progress["running"],
        "current": _valuation_progress["current"],
        "total": _valuation_progress["total"],
        "current_symbol": _valuation_progress["current_symbol"],
        "success_count": _valuation_progress["success_count"],
        "failed_count": _valuation_progress["failed_count"],
        "started_at": _valuation_progress["started_at"],
        "completed_at": _valuation_progress["completed_at"],
    }

    if _valuation_progress["total"] > 0:
        response["progress_percent"] = round(
            _valuation_progress["current"] / _valuation_progress["total"] * 100, 1
        )

    return response


def _run_valuation_refresh(symbols: List[str]):
    """Background task to refresh all valuations."""
    global _valuation_progress

    from app.database import SessionLocal

    db = SessionLocal()
    data_service = DSEDataService()
    sticker_calc = StickerPriceCalculator()
    evaluator = FourMsEvaluator()

    try:
        for i, symbol in enumerate(symbols):
            if not _valuation_progress["running"]:
                break

            _valuation_progress["current_symbol"] = symbol

            try:
                # Get financial data
                financials = db.query(FinancialData).filter(
                    FinancialData.stock_symbol == symbol
                ).order_by(FinancialData.year.asc()).all()

                if len(financials) < 2:
                    _update_stock_valuation(
                        db, symbol,
                        valuation_status="NOT_CALCULABLE",
                        valuation_note="Insufficient financial data (need at least 2 years)"
                    )
                    _valuation_progress["failed_count"] += 1
                    _valuation_progress["current"] = i + 1
                    continue

                # Extract data
                eps_history = [f.eps for f in financials if f.eps is not None]

                if len(eps_history) < 2:
                    _update_stock_valuation(
                        db, symbol,
                        valuation_status="NOT_CALCULABLE",
                        valuation_note="Insufficient EPS data"
                    )
                    _valuation_progress["failed_count"] += 1
                    _valuation_progress["current"] = i + 1
                    continue

                # Calculate sticker price
                pe_values = [f.pe_ratio for f in financials if f.pe_ratio]
                historical_pe = sum(pe_values) / len(pe_values) if pe_values else 15.0

                sticker_result = sticker_calc.calculate_from_financials(
                    eps_history=eps_history,
                    historical_pe=historical_pe,
                )

                # If not calculable, save status and continue
                if sticker_result.status == "NOT_CALCULABLE":
                    _update_stock_valuation(
                        db, symbol,
                        valuation_status="NOT_CALCULABLE",
                        valuation_note=sticker_result.note or "Sticker price not calculable"
                    )
                    _valuation_progress["failed_count"] += 1
                    _valuation_progress["current"] = i + 1
                    continue

                # Calculate 4Ms
                four_ms_result = evaluator.evaluate(
                    symbol=symbol,
                    revenue_history=[f.revenue for f in financials if f.revenue],
                    net_income_history=[f.net_income for f in financials if f.net_income],
                    roe_history=[f.roe for f in financials if f.roe],
                    gross_margin_history=[f.gross_margin for f in financials if f.gross_margin],
                    operating_margin_history=[f.operating_margin for f in financials if f.operating_margin],
                    debt_to_equity_history=[f.debt_to_equity for f in financials if f.debt_to_equity is not None],
                    fcf_history=[f.free_cash_flow for f in financials if f.free_cash_flow],
                    current_price=0,  # Don't need current price for cached score
                    sticker_price=sticker_result.sticker_price,
                )

                # Update stock record
                _update_stock_valuation(
                    db, symbol,
                    sticker_price=sticker_result.sticker_price,
                    margin_of_safety=sticker_result.margin_of_safety,
                    four_m_score=four_ms_result.overall_score,
                    four_m_grade=four_ms_result.overall_grade,
                    recommendation=sticker_result.recommendation or four_ms_result.recommendation,
                    valuation_status="CALCULABLE",
                    valuation_note=None,
                )

                _valuation_progress["success_count"] += 1

            except Exception as e:
                logger.error(f"Error calculating valuation for {symbol}: {e}")
                _update_stock_valuation(
                    db, symbol,
                    valuation_status="NOT_CALCULABLE",
                    valuation_note=f"Calculation error: {str(e)[:200]}"
                )
                _valuation_progress["failed_count"] += 1

            _valuation_progress["current"] = i + 1

    except Exception as e:
        logger.error(f"Valuation refresh error: {e}")
    finally:
        _valuation_progress["running"] = False
        _valuation_progress["completed_at"] = datetime.now().isoformat()
        db.close()


def _update_stock_valuation(
    db: Session,
    symbol: str,
    sticker_price: Optional[float] = None,
    margin_of_safety: Optional[float] = None,
    four_m_score: Optional[float] = None,
    four_m_grade: Optional[str] = None,
    recommendation: Optional[str] = None,
    valuation_status: str = "UNKNOWN",
    valuation_note: Optional[str] = None,
):
    """Update or create stock record with valuation data."""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()

    if not stock:
        stock = Stock(symbol=symbol)
        db.add(stock)

    stock.sticker_price = sticker_price
    stock.margin_of_safety = margin_of_safety
    stock.four_m_score = four_m_score
    stock.four_m_grade = four_m_grade
    stock.recommendation = recommendation
    stock.valuation_status = valuation_status
    stock.valuation_note = valuation_note
    stock.last_valuation_update = datetime.now()

    db.commit()
