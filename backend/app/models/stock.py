"""Stock model - basic stock information."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Stock(Base):
    """Stock master table - stores basic information about each DSE stock."""

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)  # e.g., "BXPHARMA"
    name = Column(String(200))  # Full company name
    sector = Column(String(100))  # e.g., "Pharmaceuticals"

    # Latest price data (cached)
    current_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    open_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)
    trade_count = Column(Integer)

    # Market data
    market_cap = Column(Float)
    total_shares = Column(Float)
    free_float = Column(Float)

    # Latest calculated values (cached for quick access)
    sticker_price = Column(Float)
    margin_of_safety = Column(Float)
    big_five_score = Column(Integer)  # 0-5
    four_m_score = Column(Float)  # 0-100

    # Recommendation
    recommendation = Column(String(20))  # "STRONG_BUY", "BUY", "HOLD", "SELL"
    discount_to_sticker = Column(Float)  # Percentage

    # Valuation status tracking
    valuation_status = Column(String(20), default="UNKNOWN")  # CALCULABLE, NOT_CALCULABLE, UNKNOWN
    valuation_note = Column(String(500))  # Reason if not calculable
    last_valuation_update = Column(DateTime)
    four_m_grade = Column(String(2))  # A, B, C, D, F

    # Metadata
    is_active = Column(Boolean, default=True)
    last_price_update = Column(DateTime)
    last_fundamental_update = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Stock {self.symbol}>"
