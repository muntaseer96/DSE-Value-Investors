"""Four Ms Evaluator - Phil Town's Rule #1 Methodology (Fully Objective).

The Four Ms framework for evaluating a business:
1. Meaning - Business predictability based on historical data patterns
2. Moat - Sustainable competitive advantage from financial metrics
3. Management - Owner-oriented management from capital allocation patterns
4. Margin of Safety - Price vs intrinsic value

ALL metrics are now calculated objectively from financial data.
No subjective user inputs required.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from .sectors import get_sector, get_sector_profile, get_sector_note


@dataclass
class MeaningScore:
    """Meaning evaluation - Business predictability and understandability.

    Calculated from:
    - Revenue stability (low volatility = more predictable)
    - Earnings consistency (profitable years)
    - Net income stability (low volatility = predictable earnings)
    - Data quality (years of data available)
    """
    revenue_stability: float  # 0-100, higher = more stable
    earnings_consistency: float  # Percentage of profitable years
    net_income_stability: float  # 0-100, higher = more stable earnings
    data_quality: float  # 0-100, based on years of data

    sector: Optional[str]  # Stock's sector
    sector_note: Optional[str]  # Bangladesh-specific sector context

    score: float  # 0-100
    grade: str  # A, B, C, D, F
    notes: List[str]

    def to_dict(self):
        return {
            "revenue_stability": round(self.revenue_stability, 1),
            "earnings_consistency": round(self.earnings_consistency, 1),
            "net_income_stability": round(self.net_income_stability, 1),
            "data_quality": round(self.data_quality, 1),
            "sector": self.sector,
            "sector_note": self.sector_note,
            "score": round(self.score, 1),
            "grade": self.grade,
            "notes": self.notes,
        }


@dataclass
class MoatScore:
    """Moat evaluation - competitive advantage indicators.

    Calculated from (100% objective):
    - ROE level and consistency
    - Gross margin level and trend
    - Operating margin level
    """
    roe_avg: float  # Average ROE over available years
    roe_consistent: bool  # ROE > 15% for most years
    gross_margin_avg: float
    gross_margin_trend: str  # "Growing", "Stable", "Declining"
    operating_margin_avg: float

    score: float  # 0-100
    grade: str  # A, B, C, D, F
    notes: List[str]

    # Score breakdown for transparency
    score_breakdown: Dict[str, float]

    def to_dict(self):
        return {
            "roe_avg": round(self.roe_avg, 2),
            "roe_consistent": self.roe_consistent,
            "gross_margin_avg": round(self.gross_margin_avg, 2),
            "gross_margin_trend": self.gross_margin_trend,
            "operating_margin_avg": round(self.operating_margin_avg, 2),
            "score": round(self.score, 1),
            "grade": self.grade,
            "notes": self.notes,
            "score_breakdown": {k: round(v, 1) for k, v in self.score_breakdown.items()},
        }


@dataclass
class ManagementScore:
    """Management evaluation - owner-orientation indicators.

    Calculated from (100% objective):
    - ROE consistency (good capital allocation)
    - Debt levels (financial prudence)
    - FCF/Net Income ratio (earnings quality)
    """
    roe_above_15: bool  # Consistent ROE > 15%
    debt_to_equity: float  # Lower is better
    debt_reasonable: bool  # D/E < 0.5 is good
    fcf_to_ni_ratio: float  # FCF / Net Income, higher = quality earnings

    score: float  # 0-100
    grade: str
    notes: List[str]

    # Score breakdown for transparency
    score_breakdown: Dict[str, float]

    def to_dict(self):
        return {
            "roe_above_15": self.roe_above_15,
            "debt_to_equity": round(self.debt_to_equity, 2) if self.debt_to_equity else None,
            "debt_reasonable": self.debt_reasonable,
            "fcf_to_ni_ratio": round(self.fcf_to_ni_ratio, 2) if self.fcf_to_ni_ratio else None,
            "score": round(self.score, 1),
            "grade": self.grade,
            "notes": self.notes,
            "score_breakdown": {k: round(v, 1) for k, v in self.score_breakdown.items()},
        }


@dataclass
class MOSScore:
    """Margin of Safety evaluation."""
    current_price: float
    sticker_price: float
    margin_of_safety: float  # 50% of sticker
    discount_pct: float  # How much below sticker

    score: float  # 0-100
    grade: str
    recommendation: str
    notes: List[str]

    def to_dict(self):
        return {
            "current_price": round(self.current_price, 2),
            "sticker_price": round(self.sticker_price, 2),
            "margin_of_safety": round(self.margin_of_safety, 2),
            "discount_pct": round(self.discount_pct, 2),
            "score": round(self.score, 1),
            "grade": self.grade,
            "recommendation": self.recommendation,
            "notes": self.notes,
        }


@dataclass
class FourMsResult:
    """Complete Four Ms evaluation result."""
    meaning: MeaningScore  # Now calculated, not user input
    moat: MoatScore
    management: ManagementScore
    mos: MOSScore

    overall_score: float  # 0-100 weighted average
    overall_grade: str
    recommendation: str
    summary: List[str]

    # Big Five validation fields
    big_five_score: int = 5  # 0-5, how many Big Five metrics passed
    big_five_penalty: int = 0  # Penalty applied to overall score
    big_five_warning: bool = False  # True if Big Five failed (< 3)

    def to_dict(self):
        return {
            "meaning": self.meaning.to_dict(),
            "moat": self.moat.to_dict(),
            "management": self.management.to_dict(),
            "mos": self.mos.to_dict(),
            "overall_score": round(self.overall_score, 1),
            "overall_grade": self.overall_grade,
            "recommendation": self.recommendation,
            "summary": self.summary,
            "big_five_score": self.big_five_score,
            "big_five_penalty": self.big_five_penalty,
            "big_five_warning": self.big_five_warning,
        }


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


class FourMsEvaluator:
    """Evaluate a stock using the Four Ms framework - Fully Objective."""

    def _calculate_average(self, values: List[float]) -> float:
        """Calculate average of non-None, non-zero values."""
        valid = [v for v in values if v is not None and v != 0]
        return sum(valid) / len(valid) if valid else 0.0

    def _calculate_cv(self, values: List[float]) -> float:
        """Calculate coefficient of variation (lower = more stable)."""
        valid = [v for v in values if v is not None and v > 0]
        if len(valid) < 2:
            return 100.0  # High CV if insufficient data
        mean = sum(valid) / len(valid)
        if mean == 0:
            return 100.0
        variance = sum((x - mean) ** 2 for x in valid) / len(valid)
        std = variance ** 0.5
        return (std / mean) * 100

    def _is_consistent(self, values: List[float], threshold: float) -> bool:
        """Check if most values meet the threshold."""
        valid = [v for v in values if v is not None]
        if len(valid) < 2:
            return False
        passing = sum(1 for v in valid if v >= threshold)
        return passing >= len(valid) * 0.6  # 60% must pass

    def _get_trend(self, values: List[float]) -> str:
        """Determine if values are growing, stable, or declining."""
        valid = [v for v in values if v is not None]
        if len(valid) < 3:
            return "Stable"

        # Compare first third to last third
        n = len(valid)
        first_third = valid[:n//3] if n >= 3 else valid[:1]
        last_third = valid[-n//3:] if n >= 3 else valid[-1:]

        avg_first = sum(first_third) / len(first_third) if first_third else 0
        avg_last = sum(last_third) / len(last_third) if last_third else 0

        if avg_first == 0:
            return "Stable"

        change_pct = ((avg_last - avg_first) / abs(avg_first)) * 100

        if change_pct > 10:
            return "Growing"
        elif change_pct < -10:
            return "Declining"
        else:
            return "Stable"

    def _calculate_profitable_years_pct(self, net_income_history: List[float]) -> float:
        """Calculate percentage of profitable years."""
        valid = [v for v in net_income_history if v is not None]
        if not valid:
            return 0.0
        profitable = sum(1 for v in valid if v > 0)
        return (profitable / len(valid)) * 100

    def evaluate_meaning(
        self,
        symbol: str,
        revenue_history: List[float],
        net_income_history: List[float],
    ) -> MeaningScore:
        """Evaluate business meaning/predictability from data patterns.

        Scoring breakdown (100 points total):
        - Revenue Stability (25): Low volatility = predictable business
        - Earnings Consistency (25): % of profitable years
        - Net Income Stability (25): Low volatility = predictable earnings
        - Data Quality (25): Years of data available
        """
        notes = []
        score_breakdown = {}

        # Get sector information
        sector = get_sector(symbol)
        sector_profile = get_sector_profile(symbol)
        sector_note = get_sector_note(symbol)
        sector_name = sector_profile.display_name if sector_profile else None

        # 1. Revenue Stability (25 points) - Lower CV = more stable
        revenue_cv = self._calculate_cv(revenue_history)
        if revenue_cv < 15:
            stability_score = 25
            notes.append("Highly stable revenue - predictable business")
        elif revenue_cv < 25:
            stability_score = 20
            notes.append("Stable revenue stream")
        elif revenue_cv < 40:
            stability_score = 15
            notes.append("Moderate revenue volatility")
        elif revenue_cv < 60:
            stability_score = 10
            notes.append("Revenue shows significant volatility")
        else:
            stability_score = 5
            notes.append("Highly volatile revenue - harder to predict")

        # Convert to 0-100 scale for display
        revenue_stability = 100 - min(100, revenue_cv)  # Higher = more stable
        score_breakdown["Revenue Stability"] = stability_score

        # 2. Earnings Consistency (25 points) - % of profitable years
        earnings_pct = self._calculate_profitable_years_pct(net_income_history)
        if earnings_pct >= 100:
            earnings_score = 25
            notes.append("Profitable every year - strong earnings quality")
        elif earnings_pct >= 80:
            earnings_score = 20
            notes.append("Profitable most years")
        elif earnings_pct >= 60:
            earnings_score = 15
        elif earnings_pct >= 40:
            earnings_score = 10
            notes.append("Inconsistent profitability")
        else:
            earnings_score = 5
            notes.append("Frequently unprofitable - high risk")

        score_breakdown["Earnings Consistency"] = earnings_score

        # 3. Net Income Stability (25 points) - Lower CV = more predictable
        # Only consider positive earnings for stability calculation
        positive_ni = [v for v in net_income_history if v is not None and v > 0]
        ni_cv = self._calculate_cv(positive_ni) if positive_ni else 100
        if ni_cv < 20:
            ni_stability_score = 25
            notes.append("Highly predictable earnings")
        elif ni_cv < 35:
            ni_stability_score = 20
            notes.append("Stable earnings pattern")
        elif ni_cv < 50:
            ni_stability_score = 15
        elif ni_cv < 70:
            ni_stability_score = 10
            notes.append("Volatile earnings - harder to predict")
        else:
            ni_stability_score = 5
            notes.append("Highly volatile earnings")

        net_income_stability = 100 - min(100, ni_cv)  # Higher = more stable
        score_breakdown["Net Income Stability"] = ni_stability_score

        # 4. Data Quality (25 points) - Years of data
        years_of_data = max(
            len([v for v in revenue_history if v is not None]),
            len([v for v in net_income_history if v is not None])
        )
        if years_of_data >= 10:
            data_score = 25
        elif years_of_data >= 7:
            data_score = 20
        elif years_of_data >= 5:
            data_score = 15
            notes.append(f"Limited history ({years_of_data} years)")
        elif years_of_data >= 3:
            data_score = 10
            notes.append(f"Short history ({years_of_data} years) - less certainty")
        else:
            data_score = 5
            notes.append("Insufficient data for confident analysis")

        data_quality = (years_of_data / 10) * 100  # 10 years = 100%
        score_breakdown["Data Quality"] = data_score

        # Add sector context
        if sector_name:
            notes.append(f"Sector: {sector_name}")

        # Calculate total score
        total_score = stability_score + earnings_score + ni_stability_score + data_score

        return MeaningScore(
            revenue_stability=revenue_stability,
            earnings_consistency=earnings_pct,
            net_income_stability=net_income_stability,
            data_quality=min(100, data_quality),
            sector=sector_name,
            sector_note=sector_note,
            score=total_score,
            grade=_score_to_grade(total_score),
            notes=notes,
        )

    def evaluate_moat(
        self,
        roe_history: List[float],
        gross_margin_history: List[float],
        operating_margin_history: List[float],
    ) -> MoatScore:
        """Evaluate competitive moat - 100% objective.

        Scoring breakdown (100 points total):
        - ROE Level (30): Average ROE scoring
        - ROE Consistency (20): Consistent > 15%
        - Gross Margin Level (20): Pricing power indicator
        - Gross Margin Trend (15): Growing/stable/declining
        - Operating Margin (15): Operational efficiency

        Note: ROE is set to None when equity is negative (aggressive stock buybacks).
        In these cases, ROE scoring uses neutral values and adds explanatory notes.
        """
        notes = []
        score_breakdown = {}

        # Filter valid ROE values (exclude None and extreme values from negative equity)
        # ROE > 100% or < -100% typically indicates near-zero or negative equity
        valid_roe = [r for r in roe_history if r is not None and -100 <= r <= 100]
        has_negative_equity = len(valid_roe) < len([r for r in roe_history if r is not None]) or (
            len(roe_history) > 0 and len(valid_roe) == 0
        )

        # 1. ROE Level (30 points)
        if valid_roe:
            roe_avg = self._calculate_average(valid_roe)
            if roe_avg >= 20:
                roe_level_score = 30
                notes.append(f"Excellent ROE of {roe_avg:.1f}% indicates strong moat")
            elif roe_avg >= 15:
                roe_level_score = 24
                notes.append(f"Good ROE of {roe_avg:.1f}% suggests competitive advantage")
            elif roe_avg >= 10:
                roe_level_score = 18
                notes.append(f"Moderate ROE of {roe_avg:.1f}%")
            elif roe_avg >= 5:
                roe_level_score = 12
                notes.append(f"Below-average ROE of {roe_avg:.1f}%")
            else:
                roe_level_score = 6
                notes.append(f"Weak ROE of {roe_avg:.1f}% - no evident moat")
        else:
            # No valid ROE data - use neutral score
            roe_avg = 0.0
            roe_level_score = 15  # Neutral (middle of 0-30 range)
            notes.append("ROE unavailable (negative equity from stock buybacks)")
        score_breakdown["ROE Level"] = roe_level_score

        # 2. ROE Consistency (20 points)
        if valid_roe and len(valid_roe) >= 2:
            roe_consistent = self._is_consistent(valid_roe, 15.0)
            if roe_consistent:
                roe_consistency_score = 20
                notes.append("Consistent ROE > 15% shows durable advantage")
            elif self._is_consistent(valid_roe, 10.0):
                roe_consistency_score = 12
            else:
                roe_consistency_score = 6
        else:
            # No valid ROE data for consistency check - use neutral score
            roe_consistent = False
            roe_consistency_score = 10  # Neutral (middle of 0-20 range)
            if has_negative_equity and not any("ROE unavailable" in n for n in notes):
                notes.append("ROE consistency cannot be measured (negative equity)")
        score_breakdown["ROE Consistency"] = roe_consistency_score

        # 3. Gross Margin Level (20 points)
        gross_margin_avg = self._calculate_average(gross_margin_history)
        if gross_margin_avg >= 40:
            gm_level_score = 20
            notes.append("High gross margins indicate pricing power")
        elif gross_margin_avg >= 30:
            gm_level_score = 15
        elif gross_margin_avg >= 20:
            gm_level_score = 10
        elif gross_margin_avg >= 10:
            gm_level_score = 6
        else:
            gm_level_score = 3
        score_breakdown["Gross Margin Level"] = gm_level_score

        # 4. Gross Margin Trend (15 points)
        gross_margin_trend = self._get_trend(gross_margin_history)
        if gross_margin_trend == "Growing":
            gm_trend_score = 15
            notes.append("Expanding gross margins - strengthening moat")
        elif gross_margin_trend == "Stable":
            gm_trend_score = 10
        else:
            gm_trend_score = 5
            notes.append("Declining gross margins - potential moat erosion")
        score_breakdown["Gross Margin Trend"] = gm_trend_score

        # 5. Operating Margin (15 points)
        operating_margin_avg = self._calculate_average(operating_margin_history)
        if operating_margin_avg >= 25:
            om_score = 15
            notes.append("Excellent operating efficiency")
        elif operating_margin_avg >= 15:
            om_score = 12
        elif operating_margin_avg >= 10:
            om_score = 8
        elif operating_margin_avg >= 5:
            om_score = 5
        else:
            om_score = 2
        score_breakdown["Operating Margin"] = om_score

        # Calculate total score
        total_score = (
            roe_level_score + roe_consistency_score +
            gm_level_score + gm_trend_score + om_score
        )

        return MoatScore(
            roe_avg=roe_avg,
            roe_consistent=roe_consistent,
            gross_margin_avg=gross_margin_avg,
            gross_margin_trend=gross_margin_trend,
            operating_margin_avg=operating_margin_avg,
            score=total_score,
            grade=_score_to_grade(total_score),
            notes=notes,
            score_breakdown=score_breakdown,
        )

    def evaluate_management(
        self,
        roe_history: List[float],
        debt_to_equity_history: List[float],
        fcf_history: List[float],
        net_income_history: List[float],
    ) -> ManagementScore:
        """Evaluate management quality - 100% objective.

        Scoring breakdown (100 points total):
        - ROE Consistency (34): Good capital allocation
        - Debt Levels (33): Financial prudence
        - FCF/NI Ratio (33): Earnings quality

        Note: ROE and D/E are set to None when equity is negative (aggressive buybacks).
        In these cases, use neutral scores and add explanatory notes.
        """
        notes = []
        score_breakdown = {}

        # Filter valid ROE values (exclude None and extreme values from negative equity)
        valid_roe = [r for r in roe_history if r is not None and -100 <= r <= 100]

        # 1. ROE Consistency (34 points)
        if valid_roe and len(valid_roe) >= 2:
            roe_above_15 = self._is_consistent(valid_roe, 15.0)
            roe_avg = self._calculate_average(valid_roe)

            if roe_above_15:
                roe_score = 34
                notes.append("Consistent ROE > 15% shows good capital allocation")
            elif self._is_consistent(valid_roe, 10.0):
                roe_score = 24
            elif roe_avg >= 10:
                roe_score = 16
            else:
                roe_score = 8
        else:
            # No valid ROE data - use neutral score
            roe_above_15 = False
            roe_score = 17  # Neutral (middle of 0-34 range)
            notes.append("Capital allocation hard to measure (negative equity from buybacks)")
        score_breakdown["ROE Consistency"] = roe_score

        # Filter valid D/E values (None indicates negative equity)
        valid_de = [d for d in debt_to_equity_history if d is not None]

        # 2. Debt Levels (33 points)
        if valid_de:
            de_avg = self._calculate_average(valid_de)
            debt_reasonable = de_avg < 0.5

            if de_avg < 0.3:
                debt_score = 33
                notes.append("Very low debt provides financial flexibility")
            elif de_avg < 0.5:
                debt_score = 26
                notes.append("Conservative debt levels")
            elif de_avg < 1.0:
                debt_score = 18
                notes.append("Moderate debt - monitor carefully")
            elif de_avg < 2.0:
                debt_score = 10
                notes.append("Elevated debt levels")
            else:
                debt_score = 5
                notes.append("High debt is a concern")
        else:
            # No valid D/E data - negative equity from buybacks
            de_avg = 0
            debt_reasonable = True  # Can't determine, assume reasonable
            debt_score = 20  # Neutral-positive (companies with negative equity often have low actual debt)
            notes.append("Debt/equity ratio N/A (negative equity)")
        score_breakdown["Debt Management"] = debt_score

        # 3. FCF/Net Income Ratio (33 points) - Earnings quality
        fcf_avg = self._calculate_average(fcf_history)
        ni_avg = self._calculate_average(net_income_history)

        if ni_avg > 0:
            fcf_ni_ratio = fcf_avg / ni_avg if ni_avg != 0 else 0
        else:
            fcf_ni_ratio = 0

        if fcf_ni_ratio >= 1.0:
            fcf_score = 33
            notes.append("FCF exceeds net income - high quality earnings")
        elif fcf_ni_ratio >= 0.8:
            fcf_score = 26
            notes.append("Strong free cash flow generation")
        elif fcf_ni_ratio >= 0.5:
            fcf_score = 18
        elif fcf_ni_ratio >= 0.2:
            fcf_score = 10
            notes.append("Weak cash conversion")
        else:
            fcf_score = 5
            notes.append("Poor cash generation vs earnings")
        score_breakdown["Cash Generation"] = fcf_score

        # Calculate total score
        total_score = roe_score + debt_score + fcf_score

        return ManagementScore(
            roe_above_15=roe_above_15,
            debt_to_equity=de_avg,
            debt_reasonable=debt_reasonable,
            fcf_to_ni_ratio=fcf_ni_ratio,
            score=total_score,
            grade=_score_to_grade(total_score),
            notes=notes,
            score_breakdown=score_breakdown,
        )

    def evaluate_mos(
        self,
        current_price: float,
        sticker_price: float,
    ) -> MOSScore:
        """Evaluate Margin of Safety."""
        notes = []
        mos = sticker_price * 0.5  # 50% margin of safety

        # Calculate discount
        if sticker_price > 0:
            discount_pct = ((sticker_price - current_price) / sticker_price) * 100
        else:
            discount_pct = 0

        # Score based on discount
        if current_price < mos:
            score = 100
            recommendation = "STRONG_BUY"
            notes.append(f"Price is {discount_pct:.1f}% below Sticker Price - excellent value!")
            notes.append("Trading below Margin of Safety - maximum safety")
        elif current_price < sticker_price:
            # Scale score from 50-90 based on discount
            if sticker_price > mos:
                discount_ratio = (sticker_price - current_price) / (sticker_price - mos)
            else:
                discount_ratio = 0.5
            score = 50 + (discount_ratio * 40)
            recommendation = "BUY"
            notes.append(f"Price is {discount_pct:.1f}% below Sticker Price - good value")
        elif current_price < sticker_price * 1.1:
            score = 40
            recommendation = "HOLD"
            notes.append("Price is near fair value - hold position")
        elif current_price < sticker_price * 1.25:
            score = 25
            recommendation = "HOLD"
            notes.append("Slightly overvalued - consider taking profits")
        else:
            score = 10
            recommendation = "SELL"
            notes.append("Significantly overvalued - consider selling")

        return MOSScore(
            current_price=current_price,
            sticker_price=sticker_price,
            margin_of_safety=mos,
            discount_pct=discount_pct,
            score=score,
            grade=_score_to_grade(score),
            recommendation=recommendation,
            notes=notes,
        )

    def evaluate(
        self,
        symbol: str,
        # Meaning data
        revenue_history: List[float] = None,
        net_income_history: List[float] = None,
        # Moat data
        roe_history: List[float] = None,
        gross_margin_history: List[float] = None,
        operating_margin_history: List[float] = None,
        # Management data
        debt_to_equity_history: List[float] = None,
        fcf_history: List[float] = None,
        # Margin of Safety
        current_price: float = 0,
        sticker_price: float = 0,
        # Big Five validation
        big_five_score: int = 5,  # 0-5, how many Big Five metrics passed
    ) -> FourMsResult:
        """Complete Four Ms evaluation - 100% objective.

        Weights:
        - Meaning: 20%
        - Moat: 30%
        - Management: 20%
        - MOS: 30%

        IMPORTANT: If Big Five fails (< 3/5 metrics at 10%+ growth):
        1. Apply graduated penalty to score: 2/5=-10, 1/5=-20, 0/5=-30
        2. Cap recommendation at HOLD regardless of MOS score
        """
        # Default empty lists
        revenue_history = revenue_history or []
        net_income_history = net_income_history or []
        roe_history = roe_history or []
        gross_margin_history = gross_margin_history or []
        operating_margin_history = operating_margin_history or []
        debt_to_equity_history = debt_to_equity_history or []
        fcf_history = fcf_history or []

        # Evaluate each M
        meaning = self.evaluate_meaning(
            symbol, revenue_history, net_income_history
        )
        moat = self.evaluate_moat(
            roe_history, gross_margin_history, operating_margin_history
        )
        management = self.evaluate_management(
            roe_history, debt_to_equity_history, fcf_history, net_income_history
        )
        mos = self.evaluate_mos(current_price, sticker_price)

        # Calculate base overall score (weighted average)
        # Meaning: 20%, Moat: 30%, Management: 20%, MOS: 30%
        base_score = (
            meaning.score * 0.20 +
            moat.score * 0.30 +
            management.score * 0.20 +
            mos.score * 0.30
        )

        # Apply Big Five penalty if score < 3 (failed)
        # Graduated penalty: 2/5=-10, 1/5=-20, 0/5=-30
        big_five_warning = big_five_score < 3
        if big_five_score == 2:
            big_five_penalty = 10
        elif big_five_score == 1:
            big_five_penalty = 20
        elif big_five_score == 0:
            big_five_penalty = 30
        else:
            big_five_penalty = 0

        # Apply penalty (minimum score is 0)
        overall_score = max(0, base_score - big_five_penalty)
        overall_grade = _score_to_grade(overall_score)

        # Generate summary
        summary = []
        if overall_score >= 70:
            summary.append("This appears to be a Rule #1 company")
        elif overall_score >= 50:
            summary.append("This company has some Rule #1 qualities but needs more analysis")
        else:
            summary.append("This company may not meet Rule #1 criteria")

        # Add key notes from each M
        if meaning.notes:
            summary.append(meaning.notes[0])
        if moat.notes:
            summary.append(moat.notes[0])
        if management.notes:
            summary.append(management.notes[0])
        if mos.notes:
            summary.append(mos.notes[0])

        # Final recommendation based on MOS and overall score
        # IMPORTANT: Cap at HOLD if Big Five fails (< 3/5 passing)
        if big_five_warning:
            # Big Five failed - can't trust sticker price, cap at HOLD
            if mos.recommendation == "SELL" or overall_score < 40:
                recommendation = "AVOID"
            else:
                recommendation = "HOLD"
            summary.insert(0, f"⚠️ Big Five failed ({big_five_score}/5) - score penalty -{big_five_penalty}, recommendation capped")
        elif mos.recommendation in ["STRONG_BUY", "BUY"] and overall_score >= 60:
            recommendation = mos.recommendation
        elif mos.recommendation == "SELL" or overall_score < 40:
            recommendation = "AVOID"
        else:
            recommendation = "HOLD"

        return FourMsResult(
            meaning=meaning,
            moat=moat,
            management=management,
            mos=mos,
            overall_score=overall_score,
            overall_grade=overall_grade,
            recommendation=recommendation,
            summary=summary,
            big_five_score=big_five_score,
            big_five_penalty=big_five_penalty,
            big_five_warning=big_five_warning,
        )
