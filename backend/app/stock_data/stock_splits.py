"""Stock split detection using yfinance.

Uses yfinance API as the source of truth for stock splits.
Finnhub's SEC filings data is NOT split-adjusted for RECENT splits,
but older splits (pre-2014) are typically already reflected in
historical EPS values from SEC filings.

We only consider splits from SPLIT_CUTOFF_YEAR onwards to avoid
double-adjusting for old splits that are already in the data.

The hardcoded FALLBACK_SPLITS dictionary is only used when yfinance
fails to return data (API issues, network problems, etc.).
"""

import logging
from typing import Dict, List, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# Only consider splits from this year onwards
# Older splits are typically already reflected in Finnhub's SEC data
SPLIT_CUTOFF_YEAR = 2014

# Cache for yfinance split data (symbol -> list of (year, ratio) tuples)
_yfinance_splits_cache: Dict[str, List[Tuple[int, float]]] = {}

# Fallback splits - only used when yfinance fails
# Format: symbol -> list of (split_year, split_ratio)
FALLBACK_SPLITS = {
    "AAPL": [(2020, 4)],
    "TSLA": [(2020, 5), (2022, 3)],
    "NVDA": [(2021, 4), (2024, 10)],
    "GOOGL": [(2022, 20)],
    "GOOG": [(2022, 20)],
    "AMZN": [(2022, 20)],
    "SHOP": [(2022, 10)],
    "NFLX": [(2015, 7)],
    "V": [(2015, 4)],
    "MA": [(2014, 10)],
    "NKE": [(2016, 2)],
    "AVGO": [(2024, 10)],
    "CMG": [(2024, 50)],
    "WMT": [(2024, 3)],
    "CTAS": [(2017, 4)],
    "TSCO": [(2022, 5)],
    "LRCX": [(2024, 10)],
    "DECK": [(2024, 6)],
    "PANW": [(2022, 3)],
    "SONY": [(2024, 5)],
    "ORLY": [(2025, 15)],
}


def _fetch_splits_from_yfinance(symbol: str) -> List[Tuple[int, float]]:
    """Fetch stock split history from yfinance.

    Only returns splits from SPLIT_CUTOFF_YEAR onwards, since older
    splits are typically already reflected in Finnhub's SEC data.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        List of (year, ratio) tuples for recent splits > 1
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        splits = ticker.splits

        if splits is None or len(splits) == 0:
            return []

        result = []
        for date, ratio in splits.items():
            # Only include recent splits (SPLIT_CUTOFF_YEAR onwards)
            # and meaningful forward splits (ratio > 1)
            if ratio > 1 and date.year >= SPLIT_CUTOFF_YEAR:
                result.append((date.year, float(ratio)))

        return result
    except ImportError:
        logger.warning("yfinance not installed, using fallback splits")
        return []
    except Exception as e:
        logger.warning(f"Failed to fetch splits for {symbol} from yfinance: {e}")
        return []


def get_splits_for_symbol(symbol: str) -> List[Tuple[int, float]]:
    """Get stock splits for a symbol, using yfinance with fallback.

    Args:
        symbol: Stock symbol

    Returns:
        List of (year, ratio) tuples sorted by year
    """
    global _yfinance_splits_cache

    # Check cache first
    if symbol in _yfinance_splits_cache:
        return _yfinance_splits_cache[symbol]

    # Try yfinance
    splits = _fetch_splits_from_yfinance(symbol)

    # If yfinance returned data, cache and return it
    if splits:
        _yfinance_splits_cache[symbol] = sorted(splits, key=lambda x: x[0])
        return _yfinance_splits_cache[symbol]

    # Fallback to hardcoded dictionary
    if symbol in FALLBACK_SPLITS:
        logger.debug(f"Using fallback splits for {symbol}")
        _yfinance_splits_cache[symbol] = FALLBACK_SPLITS[symbol]
        return FALLBACK_SPLITS[symbol]

    # No splits found
    _yfinance_splits_cache[symbol] = []
    return []


def get_eps_adjustment_factor(symbol: str, year: int) -> float:
    """Get the factor to divide raw EPS by to get split-adjusted EPS.

    Args:
        symbol: Stock symbol
        year: The fiscal year of the EPS data

    Returns:
        Factor to divide EPS by. Returns 1.0 if no adjustment needed.
    """
    splits = get_splits_for_symbol(symbol)

    if not splits:
        return 1.0

    factor = 1.0
    for split_year, split_ratio in splits:
        # If the data year is before the split year, apply the adjustment
        if year < split_year:
            factor *= split_ratio

    return factor


def adjust_eps_for_splits(symbol: str, year: int, eps: float) -> float:
    """Adjust EPS value for stock splits.

    Args:
        symbol: Stock symbol
        year: The fiscal year of the EPS data
        eps: Raw EPS value from Finnhub

    Returns:
        Split-adjusted EPS value
    """
    if eps is None:
        return None

    factor = get_eps_adjustment_factor(symbol, year)
    if factor == 1.0:
        return eps

    adjusted = round(eps / factor, 4)
    logger.debug(f"{symbol} {year}: EPS {eps} -> {adjusted} (factor: {factor})")
    return adjusted


def clear_cache():
    """Clear the yfinance splits cache."""
    global _yfinance_splits_cache
    _yfinance_splits_cache = {}


def get_cache_info() -> Dict:
    """Get information about the current cache state."""
    return {
        "cached_symbols": len(_yfinance_splits_cache),
        "symbols_with_splits": sum(1 for v in _yfinance_splits_cache.values() if v),
        "symbols": list(_yfinance_splits_cache.keys())[:20],  # First 20
    }
