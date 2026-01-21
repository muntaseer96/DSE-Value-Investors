"""
Fix stock split adjustment for US stock EPS data.

Problem: Finnhub's SEC-reported financials (/stock/financials-reported) return
EPS values as-filed, which are NOT adjusted for stock splits. This causes
CAGR calculations to show incorrect negative growth for stocks that have split.

Solution:
1. Fetch stock split history from yfinance (free)
2. Calculate cumulative split factors for each year
3. Adjust historical EPS by dividing by the split factor
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in environment")
    sys.exit(1)

# Try to import yfinance
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def fetch_stock_splits(symbol: str) -> List[Dict]:
    """Fetch stock split history from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        splits = ticker.splits

        if splits is None or len(splits) == 0:
            return []

        result = []
        for date, ratio in splits.items():
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "year": date.year,
                "ratio": float(ratio)
            })
        return result
    except Exception as e:
        print(f"  Error fetching splits for {symbol}: {e}")
        return []


def calculate_cumulative_split_factor(splits: List[Dict], for_year: int) -> float:
    """
    Calculate cumulative split factor for a given year.

    If a stock had a 7:1 split in 2014 and 4:1 in 2020:
    - For data from 2013 (before both splits): factor = 7 * 4 = 28
    - For data from 2015 (after first split, before second): factor = 4
    - For data from 2021 (after both splits): factor = 1

    The EPS should be divided by this factor to get split-adjusted values.
    """
    factor = 1.0

    for split in splits:
        split_year = split.get("year", 0)
        ratio = split.get("ratio", 1)

        # If the data year is before the split, we need to adjust
        # Only apply for splits > 1 (ignore 1:1 splits which are sometimes used for restructuring)
        if for_year < split_year and ratio > 1:
            factor *= ratio

    return factor


def get_affected_stocks() -> List[str]:
    """Get list of stocks that have financial data."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT stock_symbol
                FROM us_financial_data
                WHERE eps IS NOT NULL
                ORDER BY stock_symbol
            """)
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def get_stock_eps_data(symbol: str) -> List[Dict]:
    """Get EPS data for a stock."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, year, eps
                FROM us_financial_data
                WHERE stock_symbol = %s AND eps IS NOT NULL
                ORDER BY year
            """, (symbol,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_eps_batch(adjustments: List[Dict]):
    """Update EPS values for multiple records."""
    if not adjustments:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for adj in adjustments:
                cur.execute("""
                    UPDATE us_financial_data
                    SET eps = %s, updated_at = NOW()
                    WHERE id = %s
                """, (adj["new_eps"], adj["id"]))
            conn.commit()
    finally:
        conn.close()


def process_stock(symbol: str, dry_run: bool = True) -> Dict:
    """Process a single stock for split adjustment."""
    result = {
        "symbol": symbol,
        "splits": [],
        "adjustments": [],
        "error": None
    }

    # Fetch splits from yfinance
    splits = fetch_stock_splits(symbol)

    if not splits:
        return result

    # Filter to only meaningful splits (ratio > 1)
    meaningful_splits = [s for s in splits if s["ratio"] > 1]
    if not meaningful_splits:
        return result

    result["splits"] = meaningful_splits

    # Get current EPS data
    eps_data = get_stock_eps_data(symbol)

    if not eps_data:
        return result

    # Calculate adjustments
    for record in eps_data:
        year = record["year"]
        old_eps = float(record["eps"])

        factor = calculate_cumulative_split_factor(meaningful_splits, year)

        if factor > 1:
            new_eps = round(old_eps / factor, 4)

            adjustment = {
                "id": record["id"],
                "year": year,
                "old_eps": old_eps,
                "new_eps": new_eps,
                "factor": factor
            }
            result["adjustments"].append(adjustment)

    # Apply adjustments if not dry run
    if not dry_run and result["adjustments"]:
        update_eps_batch(result["adjustments"])

    return result


def main(dry_run: bool = True, symbols: Optional[List[str]] = None):
    """Main function to process all stocks."""
    print("=" * 60)
    print("Stock Split EPS Adjustment Tool (using yfinance)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (making changes)'}")
    print()

    # Get stocks to process
    if symbols:
        stock_list = symbols
    else:
        print("Fetching list of stocks with EPS data...")
        stock_list = get_affected_stocks()

    print(f"Processing {len(stock_list)} stocks...")
    print()

    stocks_with_splits = []
    stocks_needing_adjustment = []
    total_adjustments = 0

    for i, symbol in enumerate(stock_list):
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"  [Progress: {i + 1}/{len(stock_list)}]")

        result = process_stock(symbol, dry_run)

        if result["splits"]:
            stocks_with_splits.append(result)

            if result["adjustments"]:
                stocks_needing_adjustment.append(result)
                total_adjustments += len(result["adjustments"])
                print(f"\n{symbol}: Found {len(result['splits'])} split(s)")
                for split in result["splits"]:
                    print(f"  - {split.get('date')}: {int(split.get('ratio'))}:1 split")

                print(f"  Adjustments needed: {len(result['adjustments'])}")
                for adj in result["adjustments"][:3]:  # Show first 3
                    print(f"    {adj['year']}: ${adj['old_eps']:.2f} → ${adj['new_eps']:.4f} (÷{adj['factor']:.1f})")
                if len(result["adjustments"]) > 3:
                    print(f"    ... and {len(result['adjustments']) - 3} more")

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total stocks processed: {len(stock_list)}")
    print(f"Stocks with splits (total): {len(stocks_with_splits)}")
    print(f"Stocks needing EPS adjustment: {len(stocks_needing_adjustment)}")
    print(f"Total EPS records to adjust: {total_adjustments}")

    if dry_run and total_adjustments > 0:
        print()
        print("This was a DRY RUN. To apply changes, run with --apply flag:")
        print("  python fix_split_adjusted_eps.py --apply")

    # List affected symbols
    if stocks_needing_adjustment:
        print()
        print("Stocks needing adjustment:")
        for result in stocks_needing_adjustment:
            print(f"  - {result['symbol']}: {len(result['adjustments'])} records")

    return stocks_needing_adjustment


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix stock split EPS adjustments using yfinance")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry run)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to process")

    args = parser.parse_args()

    main(dry_run=not args.apply, symbols=args.symbols)
