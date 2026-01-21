"""Stock split history for US stocks.

Finnhub's SEC filings data is NOT split-adjusted, so we need to manually
adjust historical EPS values when saving to the database.

Format: symbol -> list of (split_year, split_ratio)
- split_year: The year the split took effect
- split_ratio: Divide pre-split EPS by this number
  e.g., 4:1 split means ratio=4, 20:1 split means ratio=20

For multiple splits, list them in chronological order.
"""

# Stock splits from 2014-2024 that affect our historical data
STOCK_SPLITS = {
    # AAPL: 4:1 split in August 2020
    "AAPL": [(2020, 4)],

    # TSLA: 5:1 (Aug 2020) + 3:1 (Aug 2022)
    "TSLA": [(2020, 5), (2022, 3)],

    # NVDA: 4:1 (July 2021) + 10:1 (June 2024)
    "NVDA": [(2021, 4), (2024, 10)],

    # GOOGL/GOOG: 20:1 split in July 2022
    "GOOGL": [(2022, 20)],
    "GOOG": [(2022, 20)],

    # AMZN: 20:1 split in June 2022
    "AMZN": [(2022, 20)],

    # SHOP: 10:1 split in June 2022
    "SHOP": [(2022, 10)],

    # NFLX: 7:1 split in July 2015
    "NFLX": [(2015, 7)],

    # V (Visa): 4:1 split in March 2015
    "V": [(2015, 4)],

    # MA (Mastercard): 10:1 split in January 2014
    "MA": [(2014, 10)],

    # NKE: 2:1 split in December 2015
    "NKE": [(2016, 2)],  # Effective in trading year 2016

    # AVGO (Broadcom): 10:1 split in July 2024
    "AVGO": [(2024, 10)],

    # CMG (Chipotle): 50:1 split in June 2024
    "CMG": [(2024, 50)],

    # WMT (Walmart): 3:1 split in February 2024
    "WMT": [(2024, 3)],

    # CTAS (Cintas): 4:1 split in September 2016
    "CTAS": [(2017, 4)],  # Effective in fiscal year 2017

    # TSCO (Tractor Supply): 5:1 split in June 2022
    "TSCO": [(2022, 5)],

    # LRCX (Lam Research): 10:1 split in March 2024
    "LRCX": [(2024, 10)],

    # DECK (Deckers): 6:1 split in September 2024
    "DECK": [(2024, 6)],

    # PANW (Palo Alto): 3:1 split in September 2022
    "PANW": [(2022, 3)],

    # SONY: 5:1 split in October 2024
    "SONY": [(2024, 5)],
}


def get_eps_adjustment_factor(symbol: str, year: int) -> float:
    """Get the factor to divide raw EPS by to get split-adjusted EPS.

    Args:
        symbol: Stock symbol
        year: The fiscal year of the EPS data

    Returns:
        Factor to divide EPS by. Returns 1.0 if no adjustment needed.
    """
    if symbol not in STOCK_SPLITS:
        return 1.0

    factor = 1.0
    for split_year, split_ratio in STOCK_SPLITS[symbol]:
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

    return round(eps / factor, 4)
