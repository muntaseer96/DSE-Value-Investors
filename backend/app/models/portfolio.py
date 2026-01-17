"""Portfolio model - tracks user's stock holdings."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class PortfolioHolding(Base):
    """User's portfolio holdings."""

    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(20), ForeignKey("stocks.symbol"), nullable=False)

    # Purchase details
    shares = Column(Integer, nullable=False)
    avg_cost = Column(Float, nullable=False)  # Average cost per share in BDT

    # Calculated fields (updated on price refresh)
    current_value = Column(Float)  # shares * current_price
    total_cost = Column(Float)  # shares * avg_cost
    profit_loss = Column(Float)  # current_value - total_cost
    profit_loss_pct = Column(Float)  # (profit_loss / total_cost) * 100

    # Notes
    notes = Column(String(500))
    buy_date = Column(DateTime)  # Optional: when purchased

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PortfolioHolding {self.stock_symbol}: {self.shares} shares>"

    def calculate_pnl(self, current_price: float):
        """Calculate P&L based on current price."""
        self.current_value = self.shares * current_price
        self.total_cost = self.shares * self.avg_cost
        self.profit_loss = self.current_value - self.total_cost
        if self.total_cost > 0:
            self.profit_loss_pct = (self.profit_loss / self.total_cost) * 100
        return self
