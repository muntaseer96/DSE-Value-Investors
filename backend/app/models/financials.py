"""Financial data models - stores historical financial statements."""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class FinancialData(Base):
    """Year-wise financial data for a stock.

    This stores the key metrics needed for Phil Town's calculations:
    - Revenue (Total Revenue)
    - EPS (Earnings Per Share)
    - Book Value / Equity
    - Operating Cash Flow
    - Free Cash Flow
    - ROE, ROA, Debt ratios
    """

    __tablename__ = "financial_data"

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(20), index=True, nullable=False)
    year = Column(Integer, nullable=False)  # e.g., 2024, 2023, etc.

    # Income Statement
    revenue = Column(Float)  # Total Revenue
    gross_profit = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)
    eps = Column(Float)  # Earnings Per Share

    # Balance Sheet
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_equity = Column(Float)  # Book Value
    total_debt = Column(Float)
    cash_and_equivalents = Column(Float)

    # Cash Flow Statement
    operating_cash_flow = Column(Float)
    capital_expenditure = Column(Float)
    free_cash_flow = Column(Float)  # Operating CF - CapEx

    # Calculated Ratios
    roe = Column(Float)  # Return on Equity (Net Income / Equity)
    roa = Column(Float)  # Return on Assets (Net Income / Assets)
    debt_to_equity = Column(Float)
    current_ratio = Column(Float)
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)

    # Per Share Data
    book_value_per_share = Column(Float)
    revenue_per_share = Column(Float)
    fcf_per_share = Column(Float)

    # PE Ratio (for reference)
    pe_ratio = Column(Float)

    # Metadata
    source = Column(String(50))  # e.g., "stocksurferbd", "manual"
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FinancialData {self.stock_symbol} {self.year}>"


class PriceHistory(Base):
    """Historical price data for charting and analysis."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(20), index=True, nullable=False)
    date = Column(DateTime, nullable=False)

    # OHLCV data
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

    # Additional fields
    adjusted_close = Column(Float)
    trade_count = Column(Integer)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<PriceHistory {self.stock_symbol} {self.date}>"
