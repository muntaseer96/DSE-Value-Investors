"""Calculator API endpoints - Sticker Price, Big Five, 4Ms."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Stock, FinancialData
from app.services import DSEDataService
from app.calculations import StickerPriceCalculator, BigFiveCalculator, FourMsEvaluator

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
