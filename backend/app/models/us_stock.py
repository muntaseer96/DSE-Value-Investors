"""US Stock models - stores US stock information and financial data."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class USStock(Base):
    """US Stock master table - stores basic information about each US stock."""

    __tablename__ = "us_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)  # e.g., "AAPL"
    name = Column(String(500))  # Full company name
    sector = Column(String(100))  # e.g., "Technology"
    market_cap = Column(BigInteger)

    # Price data (cached)
    current_price = Column(Float)
    previous_close = Column(Float)
    change = Column(Float)
    change_pct = Column(Float)
    high_52w = Column(Float)
    low_52w = Column(Float)

    # Valuations (cached)
    sticker_price = Column(Float)
    margin_of_safety = Column(Float)
    discount_to_sticker = Column(Float)
    four_m_score = Column(Float)
    four_m_grade = Column(String(2))  # A, B, C, D, F
    big_five_score = Column(Integer)  # 0-5
    big_five_warning = Column(Boolean, default=False)  # True if Big Five failed (< 3/5)
    recommendation = Column(String(20))  # "STRONG_BUY", "BUY", "HOLD", "SELL"
    valuation_status = Column(String(20), default="UNKNOWN")  # CALCULABLE, NOT_CALCULABLE, UNKNOWN
    valuation_note = Column(String(500))  # Reason if not calculable

    # Scraping metadata
    stock_type = Column(String(50))  # e.g., "Common Stock", "ETP", "ADR"
    is_sp500 = Column(Boolean, default=False)
    scrape_priority = Column(Integer, default=100)  # Lower = higher priority
    last_price_update = Column(DateTime)
    last_fundamental_update = Column(DateTime)
    last_valuation_update = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<USStock {self.symbol}>"


class USFinancialData(Base):
    """Year-wise financial data for a US stock.

    This stores the key metrics needed for Phil Town's calculations:
    - Revenue (Total Revenue)
    - EPS (Earnings Per Share)
    - Book Value / Equity
    - Operating Cash Flow
    - Free Cash Flow
    - ROE, ROA, Debt ratios
    """

    __tablename__ = "us_financial_data"

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(20), index=True, nullable=False)
    year = Column(Integer, nullable=False)  # e.g., 2024, 2023, etc.

    # Income Statement
    revenue = Column(BigInteger)  # Total Revenue
    gross_profit = Column(BigInteger)
    operating_income = Column(BigInteger)
    net_income = Column(BigInteger)
    eps = Column(Float)  # Earnings Per Share

    # Balance Sheet
    total_assets = Column(BigInteger)
    total_liabilities = Column(BigInteger)
    current_liabilities = Column(BigInteger)  # For proper ROIC calculation
    total_equity = Column(BigInteger)  # Book Value
    total_debt = Column(BigInteger)

    # Cash Flow Statement
    operating_cash_flow = Column(BigInteger)
    capital_expenditure = Column(BigInteger)
    free_cash_flow = Column(BigInteger)  # Operating CF - CapEx

    # Calculated Ratios
    roe = Column(Float)  # Return on Equity (Net Income / Equity) - None if equity <= 0
    roic = Column(Float)  # Return on Invested Capital (NOPAT / Invested Capital)
    roa = Column(Float)  # Return on Assets (Net Income / Assets)
    debt_to_equity = Column(Float)
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)

    # Metadata
    source = Column(String(50), default="finnhub")  # e.g., "finnhub"
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<USFinancialData {self.stock_symbol} {self.year}>"
