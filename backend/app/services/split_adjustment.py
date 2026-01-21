"""
Stock split adjustment service.

Automatically detects and fixes EPS values that weren't adjusted for stock splits.
Uses yfinance to get split history and applies corrections to the database.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache for split data to avoid repeated API calls
_splits_cache: Dict[str, List[Dict]] = {}


def get_stock_splits(symbol: str, use_cache: bool = True) -> List[Dict]:
    """
    Fetch stock split history from yfinance.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        use_cache: Whether to use cached data

    Returns:
        List of splits with date, year, and ratio
    """
    if use_cache and symbol in _splits_cache:
        return _splits_cache[symbol]

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        splits = ticker.splits

        if splits is None or len(splits) == 0:
            _splits_cache[symbol] = []
            return []

        result = []
        for date, ratio in splits.items():
            if ratio > 1:  # Only meaningful splits
                result.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "year": date.year,
                    "ratio": float(ratio)
                })

        _splits_cache[symbol] = result
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch splits for {symbol}: {e}")
        return []


def calculate_split_factor(splits: List[Dict], for_year: int) -> float:
    """
    Calculate cumulative split adjustment factor for a given year.

    Args:
        splits: List of splits from get_stock_splits()
        for_year: The fiscal year of the data to adjust

    Returns:
        Cumulative split factor (1.0 if no adjustment needed)
    """
    factor = 1.0

    for split in splits:
        split_year = split.get("year", 0)
        ratio = split.get("ratio", 1)

        # If the data year is before the split year, apply the factor
        if for_year < split_year and ratio > 1:
            factor *= ratio

    return factor


def get_stocks_needing_adjustment(db) -> List[Dict]:
    """
    Find all stocks in the database that have splits and need EPS adjustment.

    Args:
        db: Database session

    Returns:
        List of stocks with their splits and required adjustments
    """
    from sqlalchemy import text

    # Get all unique stock symbols with EPS data
    result = db.execute(text("""
        SELECT DISTINCT stock_symbol
        FROM us_financial_data
        WHERE eps IS NOT NULL
        ORDER BY stock_symbol
    """))
    symbols = [row[0] for row in result.fetchall()]

    stocks_needing_fix = []

    for symbol in symbols:
        splits = get_stock_splits(symbol)

        if not splits:
            continue

        # Get EPS data for this stock
        eps_result = db.execute(text("""
            SELECT id, year, eps
            FROM us_financial_data
            WHERE stock_symbol = :symbol AND eps IS NOT NULL
            ORDER BY year
        """), {"symbol": symbol})

        eps_data = [{"id": row[0], "year": row[1], "eps": float(row[2])} for row in eps_result.fetchall()]

        # Calculate adjustments needed
        adjustments = []
        for record in eps_data:
            factor = calculate_split_factor(splits, record["year"])
            if factor > 1:
                adjustments.append({
                    "id": record["id"],
                    "year": record["year"],
                    "old_eps": record["eps"],
                    "new_eps": round(record["eps"] / factor, 4),
                    "factor": factor
                })

        if adjustments:
            stocks_needing_fix.append({
                "symbol": symbol,
                "splits": splits,
                "adjustments": adjustments
            })

    return stocks_needing_fix


def apply_split_adjustments(db, dry_run: bool = True) -> Dict:
    """
    Apply split adjustments to all stocks that need them.

    Args:
        db: Database session
        dry_run: If True, don't actually make changes

    Returns:
        Summary of changes made (or would be made)
    """
    from sqlalchemy import text

    stocks = get_stocks_needing_adjustment(db)

    total_adjustments = 0
    adjusted_stocks = []

    for stock in stocks:
        symbol = stock["symbol"]
        adjustments = stock["adjustments"]

        if not dry_run:
            for adj in adjustments:
                db.execute(text("""
                    UPDATE us_financial_data
                    SET eps = :new_eps, updated_at = NOW()
                    WHERE id = :id
                """), {"new_eps": adj["new_eps"], "id": adj["id"]})

            db.commit()

        total_adjustments += len(adjustments)
        adjusted_stocks.append({
            "symbol": symbol,
            "splits": stock["splits"],
            "records_adjusted": len(adjustments),
            "sample_adjustments": adjustments[:3]  # Show first 3 as examples
        })

    return {
        "dry_run": dry_run,
        "total_stocks_adjusted": len(adjusted_stocks),
        "total_records_adjusted": total_adjustments,
        "stocks": adjusted_stocks
    }


def clear_cache():
    """Clear the splits cache."""
    global _splits_cache
    _splits_cache = {}
