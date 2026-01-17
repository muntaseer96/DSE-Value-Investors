"""Big Five Numbers Calculator - Phil Town's Rule #1 Methodology.

The Big Five Numbers measure a company's financial health and growth:
1. Revenue Growth Rate (CAGR over 5+ years)
2. EPS Growth Rate (CAGR over 5+ years)
3. Book Value (Equity) Growth Rate (CAGR over 5+ years)
4. Operating Cash Flow Growth Rate (CAGR over 5+ years)
5. Free Cash Flow Growth Rate (CAGR over 5+ years)

A company should score at least 3/5 with growth rates >10% to be considered
a good Rule #1 investment.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
import math


@dataclass
class GrowthMetric:
    """Single growth metric result."""
    name: str
    values: List[float]  # Historical values
    years: int
    cagr: float  # Growth rate as decimal
    cagr_pct: float  # Growth rate as percentage
    passes: bool  # True if CAGR >= 10%
    status: str  # "STRONG", "PASS", "WEAK", "FAIL"

    def to_dict(self):
        return {
            "name": self.name,
            "values": [round(v, 2) if v else None for v in self.values],
            "years": self.years,
            "cagr_pct": round(self.cagr_pct, 2),
            "passes": self.passes,
            "status": self.status,
        }


@dataclass
class BigFiveResult:
    """Result of Big Five analysis."""
    revenue: GrowthMetric
    eps: GrowthMetric
    equity: GrowthMetric  # Book Value
    operating_cf: GrowthMetric
    free_cf: GrowthMetric

    score: int  # 0-5, how many metrics pass
    total: int  # Always 5
    passes: bool  # True if score >= 3
    grade: str  # "A", "B", "C", "D", "F"

    def to_dict(self):
        return {
            "revenue": self.revenue.to_dict(),
            "eps": self.eps.to_dict(),
            "equity": self.equity.to_dict(),
            "operating_cf": self.operating_cf.to_dict(),
            "free_cf": self.free_cf.to_dict(),
            "score": self.score,
            "total": self.total,
            "passes": self.passes,
            "grade": self.grade,
        }


class BigFiveCalculator:
    """Calculate the Big Five Numbers for a stock."""

    # Thresholds
    STRONG_THRESHOLD = 0.15  # 15% is excellent
    PASS_THRESHOLD = 0.10  # 10% is minimum acceptable
    WEAK_THRESHOLD = 0.05  # 5% is weak but not terrible

    # Minimum years of data required
    MIN_YEARS = 3
    IDEAL_YEARS = 5

    def calculate_cagr(self, values: List[float]) -> float:
        """Calculate Compound Annual Growth Rate.

        Args:
            values: List of values in chronological order (oldest first)

        Returns:
            CAGR as decimal (e.g., 0.12 for 12%)
        """
        if not values or len(values) < 2:
            return 0.0

        # Filter out zeros and negatives for CAGR calculation
        # But keep position information
        valid_indices = [(i, v) for i, v in enumerate(values) if v and v > 0]

        if len(valid_indices) < 2:
            return 0.0

        first_idx, start_value = valid_indices[0]
        last_idx, end_value = valid_indices[-1]
        years = last_idx - first_idx

        if years <= 0 or start_value <= 0:
            return 0.0

        try:
            cagr = (end_value / start_value) ** (1 / years) - 1
            return cagr
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _evaluate_growth(self, name: str, values: List[float]) -> GrowthMetric:
        """Evaluate a single growth metric.

        Args:
            name: Metric name (e.g., "Revenue")
            values: Historical values, oldest first

        Returns:
            GrowthMetric result
        """
        cagr = self.calculate_cagr(values)
        cagr_pct = cagr * 100
        years = len(values) - 1 if len(values) > 1 else 0

        # Determine status
        if cagr >= self.STRONG_THRESHOLD:
            status = "STRONG"
            passes = True
        elif cagr >= self.PASS_THRESHOLD:
            status = "PASS"
            passes = True
        elif cagr >= self.WEAK_THRESHOLD:
            status = "WEAK"
            passes = False
        else:
            status = "FAIL"
            passes = False

        return GrowthMetric(
            name=name,
            values=values,
            years=years,
            cagr=cagr,
            cagr_pct=cagr_pct,
            passes=passes,
            status=status,
        )

    def calculate(
        self,
        revenue_history: List[float],
        eps_history: List[float],
        equity_history: List[float],
        operating_cf_history: List[float],
        free_cf_history: List[float],
    ) -> BigFiveResult:
        """Calculate all Big Five metrics.

        All lists should be in chronological order (oldest first).

        Args:
            revenue_history: Annual revenue values
            eps_history: Annual EPS values
            equity_history: Annual book value/equity values
            operating_cf_history: Annual operating cash flow values
            free_cf_history: Annual free cash flow values

        Returns:
            BigFiveResult with all metrics and overall score
        """
        # Calculate each metric
        revenue = self._evaluate_growth("Revenue", revenue_history)
        eps = self._evaluate_growth("EPS", eps_history)
        equity = self._evaluate_growth("Book Value", equity_history)
        operating_cf = self._evaluate_growth("Operating Cash Flow", operating_cf_history)
        free_cf = self._evaluate_growth("Free Cash Flow", free_cf_history)

        # Calculate overall score
        metrics = [revenue, eps, equity, operating_cf, free_cf]
        score = sum(1 for m in metrics if m.passes)

        # Determine grade
        if score == 5:
            grade = "A"
        elif score == 4:
            grade = "B"
        elif score == 3:
            grade = "C"
        elif score == 2:
            grade = "D"
        else:
            grade = "F"

        return BigFiveResult(
            revenue=revenue,
            eps=eps,
            equity=equity,
            operating_cf=operating_cf,
            free_cf=free_cf,
            score=score,
            total=5,
            passes=score >= 3,
            grade=grade,
        )

    def calculate_from_financials(
        self,
        financials: List[Dict],  # List of dicts with year-wise financial data
    ) -> BigFiveResult:
        """Calculate Big Five from financial data records.

        Args:
            financials: List of dicts, each containing:
                - year: int
                - revenue: float
                - eps: float
                - total_equity: float
                - operating_cash_flow: float
                - free_cash_flow: float

        Returns:
            BigFiveResult
        """
        # Sort by year (oldest first)
        sorted_data = sorted(financials, key=lambda x: x.get("year", 0))

        # Extract each metric series
        revenue_history = [f.get("revenue") for f in sorted_data]
        eps_history = [f.get("eps") for f in sorted_data]
        equity_history = [f.get("total_equity") for f in sorted_data]
        operating_cf_history = [f.get("operating_cash_flow") for f in sorted_data]
        free_cf_history = [f.get("free_cash_flow") for f in sorted_data]

        return self.calculate(
            revenue_history=revenue_history,
            eps_history=eps_history,
            equity_history=equity_history,
            operating_cf_history=operating_cf_history,
            free_cf_history=free_cf_history,
        )
