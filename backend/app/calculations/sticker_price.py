"""Sticker Price Calculator - Phil Town's Rule #1 Methodology.

The Sticker Price represents the intrinsic value of a stock.
The Margin of Safety (MOS) is 50% of the Sticker Price - our buy price.

Formula:
1. Get the 5-year EPS growth rate (CAGR)
2. Cap growth rate at 15% (conservative approach)
3. Use lower of historical growth rate or analyst estimate
4. Project EPS 10 years forward: Future_EPS = Current_EPS × (1 + growth_rate)^10
5. Apply PE ratio: Future_PE = min(Growth_Rate × 2, Historical_PE)
6. Calculate future price: Future_Price = Future_EPS × Future_PE
7. Discount to present value: Sticker_Price = Future_Price ÷ (1.15)^10
   (We want 15% annual return, so discount factor is 1.15^10 = 4.046)
8. Margin of Safety: MOS = Sticker_Price × 0.5 (50% discount for safety)
"""
from dataclasses import dataclass
from typing import Optional, List
import math


@dataclass
class StickerPriceResult:
    """Result of Sticker Price calculation with all intermediate values."""

    # Inputs
    current_eps: float
    eps_growth_rate: float  # Historical 5-year CAGR
    used_growth_rate: float  # Actual rate used (capped at 15%)
    historical_pe: float

    # Intermediate calculations
    future_eps: float  # EPS in 10 years
    future_pe: float  # PE ratio to apply
    future_price: float  # Price in 10 years

    # Final values
    sticker_price: float
    margin_of_safety: float

    # Current price comparison
    current_price: Optional[float] = None
    discount_to_sticker: Optional[float] = None  # Percentage
    discount_to_mos: Optional[float] = None  # Percentage
    recommendation: Optional[str] = None

    def to_dict(self):
        return {
            "current_eps": round(self.current_eps, 2),
            "eps_growth_rate": round(self.eps_growth_rate * 100, 2),  # as percentage
            "used_growth_rate": round(self.used_growth_rate * 100, 2),
            "historical_pe": round(self.historical_pe, 2),
            "future_eps": round(self.future_eps, 2),
            "future_pe": round(self.future_pe, 2),
            "future_price": round(self.future_price, 2),
            "sticker_price": round(self.sticker_price, 2),
            "margin_of_safety": round(self.margin_of_safety, 2),
            "current_price": round(self.current_price, 2) if self.current_price else None,
            "discount_to_sticker": round(self.discount_to_sticker, 2) if self.discount_to_sticker else None,
            "discount_to_mos": round(self.discount_to_mos, 2) if self.discount_to_mos else None,
            "recommendation": self.recommendation,
        }


class StickerPriceCalculator:
    """Calculate Sticker Price and Margin of Safety using Phil Town's method."""

    # Constants
    MAX_GROWTH_RATE = 0.15  # Cap at 15%
    MIN_GROWTH_RATE = 0.01  # Minimum 1% for defensive stocks
    DEFAULT_PE_MULTIPLE = 2  # PE = Growth Rate × 2
    PROJECTION_YEARS = 10
    REQUIRED_RETURN = 0.15  # 15% annual return
    MOS_DISCOUNT = 0.5  # 50% margin of safety

    def __init__(self):
        # Discount factor for 15% return over 10 years
        self.discount_factor = (1 + self.REQUIRED_RETURN) ** self.PROJECTION_YEARS

    def calculate_cagr(self, values: List[float]) -> float:
        """Calculate Compound Annual Growth Rate from a list of values.

        Args:
            values: List of values in chronological order (oldest first)

        Returns:
            CAGR as a decimal (e.g., 0.12 for 12%)
        """
        if not values or len(values) < 2:
            return 0.0

        # Filter out zeros and negatives
        valid_values = [v for v in values if v and v > 0]
        if len(valid_values) < 2:
            return 0.0

        start_value = valid_values[0]
        end_value = valid_values[-1]
        years = len(valid_values) - 1

        if start_value <= 0 or end_value <= 0 or years <= 0:
            return 0.0

        try:
            cagr = (end_value / start_value) ** (1 / years) - 1
            return cagr
        except (ValueError, ZeroDivisionError):
            return 0.0

    def calculate(
        self,
        current_eps: float,
        eps_growth_rate: float,  # As decimal, e.g., 0.12 for 12%
        historical_pe: float,
        current_price: Optional[float] = None,
        analyst_growth_rate: Optional[float] = None,
    ) -> StickerPriceResult:
        """Calculate Sticker Price and Margin of Safety.

        Args:
            current_eps: Current (TTM) Earnings Per Share
            eps_growth_rate: Historical 5-year EPS CAGR as decimal
            historical_pe: Historical average PE ratio
            current_price: Current stock price (for comparison)
            analyst_growth_rate: Analyst estimated growth rate (optional)

        Returns:
            StickerPriceResult with all calculation details
        """
        # Step 1: Determine growth rate to use
        # Use lower of historical or analyst estimate, cap at 15%
        if analyst_growth_rate is not None:
            base_growth = min(eps_growth_rate, analyst_growth_rate)
        else:
            base_growth = eps_growth_rate

        # Cap growth rate between MIN and MAX
        used_growth_rate = max(
            self.MIN_GROWTH_RATE,
            min(base_growth, self.MAX_GROWTH_RATE)
        )

        # Step 2: Project EPS 10 years forward
        future_eps = current_eps * ((1 + used_growth_rate) ** self.PROJECTION_YEARS)

        # Step 3: Calculate future PE ratio
        # PE = Growth Rate × 2, or use historical PE if lower
        growth_pe = used_growth_rate * 100 * self.DEFAULT_PE_MULTIPLE  # e.g., 15% -> PE of 30
        future_pe = min(growth_pe, historical_pe) if historical_pe > 0 else growth_pe

        # Ensure PE is reasonable (between 5 and 50)
        future_pe = max(5, min(50, future_pe))

        # Step 4: Calculate future price
        future_price = future_eps * future_pe

        # Step 5: Discount to present value (Sticker Price)
        sticker_price = future_price / self.discount_factor

        # Step 6: Calculate Margin of Safety (50% of Sticker)
        margin_of_safety = sticker_price * self.MOS_DISCOUNT

        # Create result object
        result = StickerPriceResult(
            current_eps=current_eps,
            eps_growth_rate=eps_growth_rate,
            used_growth_rate=used_growth_rate,
            historical_pe=historical_pe,
            future_eps=future_eps,
            future_pe=future_pe,
            future_price=future_price,
            sticker_price=sticker_price,
            margin_of_safety=margin_of_safety,
        )

        # Calculate comparison metrics if current price provided
        if current_price and current_price > 0:
            result.current_price = current_price

            # Discount to Sticker Price (negative means overvalued)
            result.discount_to_sticker = ((sticker_price - current_price) / sticker_price) * 100

            # Discount to MOS (negative means above MOS)
            result.discount_to_mos = ((margin_of_safety - current_price) / margin_of_safety) * 100

            # Generate recommendation
            result.recommendation = self._get_recommendation(
                current_price, sticker_price, margin_of_safety
            )

        return result

    def _get_recommendation(
        self,
        current_price: float,
        sticker_price: float,
        mos: float
    ) -> str:
        """Generate buy/hold/sell recommendation.

        Rules:
        - STRONG_BUY: Current price < MOS (50% below Sticker)
        - BUY: MOS <= Current price < Sticker Price
        - HOLD: Sticker <= Current price < 1.25 × Sticker (up to 25% premium)
        - SELL: Current price >= 1.25 × Sticker (more than 25% overvalued)
        """
        if current_price < mos:
            return "STRONG_BUY"
        elif current_price < sticker_price:
            return "BUY"
        elif current_price < sticker_price * 1.25:
            return "HOLD"
        else:
            return "SELL"

    def calculate_from_financials(
        self,
        eps_history: List[float],  # Last 5-6 years EPS, oldest first
        historical_pe: float,
        current_price: Optional[float] = None,
    ) -> StickerPriceResult:
        """Calculate Sticker Price directly from EPS history.

        Args:
            eps_history: List of EPS values (oldest to newest)
            historical_pe: Average historical PE ratio
            current_price: Current stock price

        Returns:
            StickerPriceResult
        """
        # Calculate EPS growth rate
        eps_growth_rate = self.calculate_cagr(eps_history)

        # Use most recent EPS as current
        current_eps = eps_history[-1] if eps_history else 0

        return self.calculate(
            current_eps=current_eps,
            eps_growth_rate=eps_growth_rate,
            historical_pe=historical_pe,
            current_price=current_price,
        )
