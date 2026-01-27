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
    status: str  # "STRONG", "PASS", "WEAK", "FAIL", "NEGATIVE", "NO_DATA", "INCONSISTENT"
    note: Optional[str] = None  # Explanation for special cases

    def to_dict(self):
        result = {
            "name": self.name,
            "values": [round(v, 2) if v else None for v in self.values],
            "years": self.years,
            "cagr_pct": round(self.cagr_pct, 2) if self.cagr_pct is not None else None,
            "passes": self.passes,
            "status": self.status,
        }
        if self.note:
            result["note"] = self.note
        return result


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

    def calculate_cagr(self, values: List[float], years_list: List[int] = None) -> float:
        """Calculate Compound Annual Growth Rate.

        Args:
            values: List of values in chronological order (oldest first)
            years_list: Optional list of actual years corresponding to values.
                       If provided, uses actual year span instead of array indices.
                       This fixes CAGR inflation when negative years are filtered out.

        Returns:
            CAGR as decimal (e.g., 0.12 for 12%)
        """
        if not values or len(values) < 2:
            return 0.0

        # Filter out zeros and negatives for CAGR calculation
        # Keep position information and optionally the actual year
        if years_list and len(years_list) == len(values):
            # Store (index, value, year) tuples
            valid_data = [(i, v, years_list[i]) for i, v in enumerate(values) if v and v > 0]
        else:
            # Fallback: store (index, value, None) tuples
            valid_data = [(i, v, None) for i, v in enumerate(values) if v and v > 0]

        if len(valid_data) < 2:
            return 0.0

        first_idx, start_value, first_year = valid_data[0]
        last_idx, end_value, last_year = valid_data[-1]

        # Calculate year span - prefer actual years over indices
        if first_year is not None and last_year is not None:
            year_span = last_year - first_year
        else:
            year_span = last_idx - first_idx

        if year_span <= 0 or start_value <= 0:
            return 0.0

        try:
            cagr = (end_value / start_value) ** (1 / year_span) - 1
            return cagr
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _analyze_values(self, values: List[float]) -> Dict:
        """Analyze values to detect patterns (negative, inconsistent, etc.)."""
        if not values:
            return {"pattern": "no_data", "positive": 0, "negative": 0, "zero_null": 0}

        positive = sum(1 for v in values if v and v > 0)
        negative = sum(1 for v in values if v and v < 0)
        zero_null = sum(1 for v in values if not v or v == 0)
        total_valid = positive + negative

        if total_valid == 0:
            return {"pattern": "no_data", "positive": 0, "negative": 0, "zero_null": len(values)}

        neg_ratio = negative / total_valid if total_valid > 0 else 0

        if neg_ratio >= 0.7:  # 70%+ negative
            return {"pattern": "negative", "positive": positive, "negative": negative, "zero_null": zero_null}
        elif neg_ratio >= 0.3:  # 30-70% negative = inconsistent
            return {"pattern": "inconsistent", "positive": positive, "negative": negative, "zero_null": zero_null}
        else:
            return {"pattern": "normal", "positive": positive, "negative": negative, "zero_null": zero_null}

    def _evaluate_growth(self, name: str, values: List[float], years_list: List[int] = None) -> GrowthMetric:
        """Evaluate a single growth metric.

        Args:
            name: Metric name (e.g., "Revenue")
            values: Historical values, oldest first
            years_list: Optional list of actual years corresponding to values.
                       Passed to calculate_cagr for accurate year span calculation.

        Returns:
            GrowthMetric result
        """
        years = len(values) - 1 if len(values) > 1 else 0

        # Analyze values for special patterns
        analysis = self._analyze_values(values)

        # Handle special cases first
        if analysis["pattern"] == "no_data":
            return GrowthMetric(
                name=name,
                values=values,
                years=years,
                cagr=0.0,
                cagr_pct=None,
                passes=False,
                status="NO_DATA",
                note="Insufficient data to calculate growth rate",
            )

        if analysis["pattern"] == "negative":
            return GrowthMetric(
                name=name,
                values=values,
                years=years,
                cagr=0.0,
                cagr_pct=None,
                passes=False,
                status="NEGATIVE",
                note=f"Mostly negative values ({analysis['negative']} of {analysis['positive'] + analysis['negative']} years) - cash burning",
            )

        if analysis["pattern"] == "inconsistent":
            # Still calculate CAGR for positive values, but flag as inconsistent
            cagr = self.calculate_cagr(values, years_list)
            cagr_pct = cagr * 100
            return GrowthMetric(
                name=name,
                values=values,
                years=years,
                cagr=cagr,
                cagr_pct=cagr_pct,
                passes=False,  # Inconsistent = fail regardless of CAGR
                status="INCONSISTENT",
                note=f"Fluctuating between positive ({analysis['positive']}) and negative ({analysis['negative']}) years",
            )

        # Normal case - calculate CAGR
        cagr = self.calculate_cagr(values, years_list)
        cagr_pct = cagr * 100

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
        years_list: List[int] = None,
    ) -> BigFiveResult:
        """Calculate all Big Five metrics.

        All lists should be in chronological order (oldest first).

        Args:
            revenue_history: Annual revenue values
            eps_history: Annual EPS values
            equity_history: Annual book value/equity values
            operating_cf_history: Annual operating cash flow values
            free_cf_history: Annual free cash flow values
            years_list: Optional list of actual years corresponding to the data.
                       Used for accurate CAGR calculation when values have gaps.

        Returns:
            BigFiveResult with all metrics and overall score
        """
        # Calculate each metric
        revenue = self._evaluate_growth("Revenue", revenue_history, years_list)
        eps = self._evaluate_growth("EPS", eps_history, years_list)
        equity = self._evaluate_growth("Book Value", equity_history, years_list)
        operating_cf = self._evaluate_growth("Operating Cash Flow", operating_cf_history, years_list)
        free_cf = self._evaluate_growth("Free Cash Flow", free_cf_history, years_list)

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

        # Extract years list for accurate CAGR calculation
        years_list = [f.get("year") for f in sorted_data]

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
            years_list=years_list,
        )
