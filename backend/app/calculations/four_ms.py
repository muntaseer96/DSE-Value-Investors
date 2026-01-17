"""Four Ms Evaluator - Phil Town's Rule #1 Methodology.

The Four Ms framework for evaluating a business:
1. Meaning - Do I understand and believe in the business?
2. Moat - Does it have a sustainable competitive advantage?
3. Management - Is management owner-oriented and capable?
4. Margin of Safety - Is the stock priced below intrinsic value?

Meaning is subjective (user input).
Moat, Management, and Margin of Safety can be partially calculated from financials.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class MoatScore:
    """Moat evaluation - competitive advantage indicators."""
    roe_avg: float  # Average ROE over 5 years
    roe_consistent: bool  # ROE > 15% for most years
    gross_margin_avg: float
    gross_margin_stable: bool  # Not declining
    market_position: Optional[str]  # User input: "Leader", "Strong", "Average", "Weak"

    score: float  # 0-100
    grade: str  # A, B, C, D, F
    notes: List[str]

    def to_dict(self):
        return {
            "roe_avg": round(self.roe_avg, 2),
            "roe_consistent": self.roe_consistent,
            "gross_margin_avg": round(self.gross_margin_avg, 2),
            "gross_margin_stable": self.gross_margin_stable,
            "market_position": self.market_position,
            "score": round(self.score, 1),
            "grade": self.grade,
            "notes": self.notes,
        }


@dataclass
class ManagementScore:
    """Management evaluation - owner-orientation indicators."""
    roe_above_15: bool  # Consistent ROE > 15%
    debt_to_equity: float  # Lower is better
    debt_reasonable: bool  # D/E < 0.5 is good
    insider_ownership: Optional[float]  # User input
    capital_allocation: Optional[str]  # User input

    score: float  # 0-100
    grade: str
    notes: List[str]

    def to_dict(self):
        return {
            "roe_above_15": self.roe_above_15,
            "debt_to_equity": round(self.debt_to_equity, 2) if self.debt_to_equity else None,
            "debt_reasonable": self.debt_reasonable,
            "insider_ownership": self.insider_ownership,
            "capital_allocation": self.capital_allocation,
            "score": round(self.score, 1),
            "grade": self.grade,
            "notes": self.notes,
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
    meaning_score: Optional[float]  # User-provided 0-100
    meaning_notes: Optional[str]

    moat: MoatScore
    management: ManagementScore
    mos: MOSScore

    overall_score: float  # 0-100 weighted average
    overall_grade: str
    recommendation: str
    summary: List[str]

    def to_dict(self):
        return {
            "meaning_score": self.meaning_score,
            "meaning_notes": self.meaning_notes,
            "moat": self.moat.to_dict(),
            "management": self.management.to_dict(),
            "mos": self.mos.to_dict(),
            "overall_score": round(self.overall_score, 1),
            "overall_grade": self.overall_grade,
            "recommendation": self.recommendation,
            "summary": self.summary,
        }


class FourMsEvaluator:
    """Evaluate a stock using the Four Ms framework."""

    def _calculate_average(self, values: List[float]) -> float:
        """Calculate average of non-None, non-zero values."""
        valid = [v for v in values if v is not None and v != 0]
        return sum(valid) / len(valid) if valid else 0.0

    def _is_consistent(self, values: List[float], threshold: float) -> bool:
        """Check if most values meet the threshold."""
        valid = [v for v in values if v is not None]
        if len(valid) < 2:
            return False
        passing = sum(1 for v in valid if v >= threshold)
        return passing >= len(valid) * 0.6  # 60% must pass

    def _is_stable_or_growing(self, values: List[float]) -> bool:
        """Check if values are stable or growing (not declining)."""
        valid = [v for v in values if v is not None]
        if len(valid) < 2:
            return True
        # Check if trend is not significantly declining
        first_half = valid[:len(valid)//2]
        second_half = valid[len(valid)//2:]
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0
        # Allow up to 10% decline
        return avg_second >= avg_first * 0.9

    def evaluate_moat(
        self,
        roe_history: List[float],
        gross_margin_history: List[float],
        market_position: Optional[str] = None,
    ) -> MoatScore:
        """Evaluate competitive moat.

        Args:
            roe_history: ROE values (oldest first)
            gross_margin_history: Gross margin values (oldest first)
            market_position: User assessment of market position

        Returns:
            MoatScore
        """
        notes = []

        # ROE analysis
        roe_avg = self._calculate_average(roe_history)
        roe_consistent = self._is_consistent(roe_history, 15.0)

        if roe_avg >= 20:
            notes.append(f"Excellent ROE of {roe_avg:.1f}% indicates strong moat")
        elif roe_avg >= 15:
            notes.append(f"Good ROE of {roe_avg:.1f}% suggests competitive advantage")
        else:
            notes.append(f"ROE of {roe_avg:.1f}% is below the 15% threshold")

        # Gross margin analysis
        gross_margin_avg = self._calculate_average(gross_margin_history)
        gross_margin_stable = self._is_stable_or_growing(gross_margin_history)

        if gross_margin_avg >= 40:
            notes.append("High gross margins indicate pricing power")
        elif not gross_margin_stable:
            notes.append("Declining gross margins may indicate weakening moat")

        # Calculate score
        score = 0
        # ROE contribution (40 points max)
        if roe_avg >= 20:
            score += 40
        elif roe_avg >= 15:
            score += 30
        elif roe_avg >= 10:
            score += 20
        else:
            score += 10

        # ROE consistency (20 points)
        if roe_consistent:
            score += 20

        # Gross margin (20 points)
        if gross_margin_avg >= 40:
            score += 20
        elif gross_margin_avg >= 30:
            score += 15
        elif gross_margin_avg >= 20:
            score += 10

        # Gross margin stability (10 points)
        if gross_margin_stable:
            score += 10

        # Market position (10 points)
        position_scores = {"Leader": 10, "Strong": 7, "Average": 4, "Weak": 0}
        score += position_scores.get(market_position, 5)

        # Determine grade
        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 55:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"

        return MoatScore(
            roe_avg=roe_avg,
            roe_consistent=roe_consistent,
            gross_margin_avg=gross_margin_avg,
            gross_margin_stable=gross_margin_stable,
            market_position=market_position,
            score=score,
            grade=grade,
            notes=notes,
        )

    def evaluate_management(
        self,
        roe_history: List[float],
        debt_to_equity_history: List[float],
        insider_ownership: Optional[float] = None,
        capital_allocation: Optional[str] = None,
    ) -> ManagementScore:
        """Evaluate management quality.

        Args:
            roe_history: ROE values (oldest first)
            debt_to_equity_history: D/E ratio values (oldest first)
            insider_ownership: Percentage of insider ownership
            capital_allocation: User assessment ("Excellent", "Good", "Average", "Poor")

        Returns:
            ManagementScore
        """
        notes = []

        # ROE analysis
        roe_above_15 = self._is_consistent(roe_history, 15.0)
        if roe_above_15:
            notes.append("Consistent ROE > 15% shows good capital allocation")

        # Debt analysis
        de_avg = self._calculate_average(debt_to_equity_history)
        debt_reasonable = de_avg < 0.5 if de_avg else True

        if de_avg < 0.3:
            notes.append("Very low debt provides financial flexibility")
        elif de_avg < 0.5:
            notes.append("Reasonable debt levels")
        elif de_avg < 1.0:
            notes.append("Moderate debt - monitor carefully")
        else:
            notes.append("High debt levels are a concern")

        # Calculate score
        score = 0

        # ROE > 15% consistently (30 points)
        if roe_above_15:
            score += 30
        elif self._calculate_average(roe_history) >= 10:
            score += 15

        # Debt levels (30 points)
        if de_avg < 0.3:
            score += 30
        elif de_avg < 0.5:
            score += 25
        elif de_avg < 1.0:
            score += 15
        else:
            score += 5

        # Insider ownership (20 points)
        if insider_ownership is not None:
            if insider_ownership >= 20:
                score += 20
                notes.append(f"High insider ownership ({insider_ownership:.1f}%) aligns interests")
            elif insider_ownership >= 10:
                score += 15
            elif insider_ownership >= 5:
                score += 10
        else:
            score += 10  # Neutral if unknown

        # Capital allocation (20 points)
        allocation_scores = {"Excellent": 20, "Good": 15, "Average": 10, "Poor": 0}
        score += allocation_scores.get(capital_allocation, 10)

        # Determine grade
        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 55:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"

        return ManagementScore(
            roe_above_15=roe_above_15,
            debt_to_equity=de_avg,
            debt_reasonable=debt_reasonable,
            insider_ownership=insider_ownership,
            capital_allocation=capital_allocation,
            score=score,
            grade=grade,
            notes=notes,
        )

    def evaluate_mos(
        self,
        current_price: float,
        sticker_price: float,
    ) -> MOSScore:
        """Evaluate Margin of Safety.

        Args:
            current_price: Current stock price
            sticker_price: Calculated sticker price

        Returns:
            MOSScore
        """
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
            discount_ratio = (sticker_price - current_price) / (sticker_price - mos)
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

        # Determine grade
        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 50:
            grade = "C"
        elif score >= 30:
            grade = "D"
        else:
            grade = "F"

        return MOSScore(
            current_price=current_price,
            sticker_price=sticker_price,
            margin_of_safety=mos,
            discount_pct=discount_pct,
            score=score,
            grade=grade,
            recommendation=recommendation,
            notes=notes,
        )

    def evaluate(
        self,
        # Meaning (user input)
        meaning_score: Optional[float] = None,
        meaning_notes: Optional[str] = None,
        # Moat
        roe_history: List[float] = None,
        gross_margin_history: List[float] = None,
        market_position: Optional[str] = None,
        # Management
        debt_to_equity_history: List[float] = None,
        insider_ownership: Optional[float] = None,
        capital_allocation: Optional[str] = None,
        # Margin of Safety
        current_price: float = 0,
        sticker_price: float = 0,
    ) -> FourMsResult:
        """Complete Four Ms evaluation.

        Returns:
            FourMsResult with all evaluations
        """
        # Default empty lists
        roe_history = roe_history or []
        gross_margin_history = gross_margin_history or []
        debt_to_equity_history = debt_to_equity_history or []

        # Evaluate each M
        moat = self.evaluate_moat(roe_history, gross_margin_history, market_position)
        management = self.evaluate_management(
            roe_history, debt_to_equity_history, insider_ownership, capital_allocation
        )
        mos = self.evaluate_mos(current_price, sticker_price)

        # Calculate overall score (weighted average)
        # Meaning: 20%, Moat: 30%, Management: 20%, MOS: 30%
        meaning = meaning_score if meaning_score is not None else 50  # Neutral if not provided
        overall_score = (
            meaning * 0.20 +
            moat.score * 0.30 +
            management.score * 0.20 +
            mos.score * 0.30
        )

        # Determine overall grade
        if overall_score >= 85:
            overall_grade = "A"
        elif overall_score >= 70:
            overall_grade = "B"
        elif overall_score >= 55:
            overall_grade = "C"
        elif overall_score >= 40:
            overall_grade = "D"
        else:
            overall_grade = "F"

        # Generate summary
        summary = []
        if overall_score >= 70:
            summary.append("This appears to be a Rule #1 company")
        elif overall_score >= 50:
            summary.append("This company has some Rule #1 qualities but needs more analysis")
        else:
            summary.append("This company may not meet Rule #1 criteria")

        summary.extend(moat.notes[:1])  # Add top moat note
        summary.extend(management.notes[:1])  # Add top management note
        summary.extend(mos.notes[:1])  # Add top MOS note

        # Final recommendation based on MOS and overall score
        if mos.recommendation in ["STRONG_BUY", "BUY"] and overall_score >= 60:
            recommendation = mos.recommendation
        elif mos.recommendation == "SELL" or overall_score < 40:
            recommendation = "AVOID"
        else:
            recommendation = "HOLD"

        return FourMsResult(
            meaning_score=meaning_score,
            meaning_notes=meaning_notes,
            moat=moat,
            management=management,
            mos=mos,
            overall_score=overall_score,
            overall_grade=overall_grade,
            recommendation=recommendation,
            summary=summary,
        )
