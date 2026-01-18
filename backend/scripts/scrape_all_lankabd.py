#!/usr/bin/env python3
"""
Scrape all DSE stocks from LankaBD and save to Supabase.

Usage:
    python scripts/scrape_all_lankabd.py [--start-from SYMBOL] [--limit N]

Examples:
    python scripts/scrape_all_lankabd.py                    # Scrape all
    python scripts/scrape_all_lankabd.py --start-from BATA  # Resume from BATA
    python scripts/scrape_all_lankabd.py --limit 10         # Only scrape 10 stocks
"""
import asyncio
import argparse
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.lankabd_scraper import LankaBDScraper
from app.services.dse_data import DSEDataService


# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://kjjringoshpczqttxaib.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


async def get_all_symbols() -> List[str]:
    """Get all DSE stock symbols from bdshare/stocksurferbd."""
    print("Fetching all stock symbols...")
    try:
        dse = DSEDataService()
        df = dse.get_current_prices()

        # Find the symbol column
        symbol_col = None
        for col in ['trading_code', 'symbol', 'code', 'ticker']:
            if col in df.columns:
                symbol_col = col
                break

        if symbol_col and not df.empty:
            symbols = sorted(df[symbol_col].dropna().unique().tolist())
            print(f"Found {len(symbols)} stocks")
            return symbols
        else:
            print(f"No symbol column found. Columns: {df.columns.tolist()}")
            return []
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        import traceback
        traceback.print_exc()
        return []


async def get_already_scraped_symbols() -> set:
    """Get symbols that already have LankaBD data in Supabase."""
    # For now, return the ones we know we've scraped
    # In production, you'd query Supabase
    return {"BXPHARMA", "SQURPHARMA", "MARICO", "OLYMPIC"}


def save_to_json(symbol: str, data: List[Dict[str, Any]], output_file: str) -> bool:
    """Append scraped data to JSON file for later Supabase import.

    Returns True if successful, False otherwise.
    """
    import json

    try:
        # Load existing data
        existing = []
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                existing = json.load(f)

        # Add new records
        for year_data in data:
            record = {
                "stock_symbol": symbol,
                "year": year_data.get("year"),
                "revenue": year_data.get("revenue"),
                "gross_profit": year_data.get("gross_profit"),
                "operating_income": year_data.get("operating_income"),
                "net_income": year_data.get("net_income"),
                "eps": year_data.get("eps"),
                "total_assets": year_data.get("total_assets"),
                "total_equity": year_data.get("total_equity"),
                "total_debt": year_data.get("total_debt"),
                "operating_cash_flow": year_data.get("operating_cash_flow"),
                "capital_expenditure": year_data.get("capital_expenditure"),
                "free_cash_flow": year_data.get("free_cash_flow"),
                "source": "lankabd",
            }
            existing.append(record)

        # Save back
        with open(output_file, 'w') as f:
            json.dump(existing, f, indent=2)

        return True
    except Exception as e:
        print(f"  [ERROR] Failed to save to JSON: {e}")
        return False


async def scrape_all(
    start_from: str = None,
    limit: int = None,
    delay: float = 2.0,
    output_file: str = "scraped_financial_data.json"
):
    """Main scraping function."""
    # Get all symbols
    all_symbols = await get_all_symbols()
    if not all_symbols:
        print("No symbols found. Exiting.")
        return

    # Filter out already scraped
    already_scraped = await get_already_scraped_symbols()
    symbols = [s for s in all_symbols if s not in already_scraped]
    print(f"Skipping {len(already_scraped)} already scraped: {already_scraped}")
    print(f"Will scrape {len(symbols)} stocks")

    # Start from specific symbol if specified
    if start_from:
        try:
            start_idx = symbols.index(start_from)
            symbols = symbols[start_idx:]
            print(f"Starting from {start_from} (index {start_idx})")
        except ValueError:
            print(f"Symbol {start_from} not found in list")
            return

    # Apply limit
    if limit:
        symbols = symbols[:limit]
        print(f"Limited to {limit} stocks")

    # Stats
    total = len(symbols)
    success = 0
    failed = []

    print(f"\n{'='*60}")
    print(f"Starting scrape of {total} stocks at {datetime.now()}")
    print(f"{'='*60}\n")

    async with LankaBDScraper() as scraper:
        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{total}] Scraping {symbol}...", end=" ")

            try:
                result = await scraper.scrape_stock(symbol)

                if result["success"] and result.get("data"):
                    years = [d.get("year") for d in result["data"]]
                    print(f"OK - {len(years)} years: {min(years)}-{max(years)}")

                    # Check if we got the important fields
                    sample = result["data"][-1]  # Latest year
                    has_ocf = sample.get("operating_cash_flow") is not None
                    has_equity = sample.get("total_equity") is not None

                    if has_ocf and has_equity:
                        print(f"       OCF: {sample.get('operating_cash_flow'):,.0f}, Equity: {sample.get('total_equity'):,.0f}")
                    else:
                        print(f"       [WARN] Missing: OCF={has_ocf}, Equity={has_equity}")

                    # Save to JSON file
                    if save_to_json(symbol, result["data"], output_file):
                        success += 1
                    else:
                        failed.append((symbol, "JSON save failed"))
                else:
                    error = result.get("error", "Unknown error")
                    print(f"FAILED - {error}")
                    failed.append((symbol, error))

            except Exception as e:
                print(f"ERROR - {e}")
                failed.append((symbol, str(e)))

            # Rate limiting
            if i < total - 1:
                await asyncio.sleep(delay)

    # Summary
    print(f"\n{'='*60}")
    print(f"COMPLETED at {datetime.now()}")
    print(f"{'='*60}")
    print(f"Total: {total}")
    print(f"Success: {success}")
    print(f"Failed: {len(failed)}")

    if success > 0:
        print(f"\nData saved to: {output_file}")

    if failed:
        print(f"\nFailed stocks:")
        for symbol, error in failed:
            print(f"  - {symbol}: {error}")

        # Save failed list for retry
        with open("failed_scrapes.txt", "w") as f:
            for symbol, error in failed:
                f.write(f"{symbol}\t{error}\n")
        print(f"Failed list saved to failed_scrapes.txt")


def main():
    parser = argparse.ArgumentParser(description="Scrape LankaBD financial data")
    parser.add_argument("--start-from", help="Start from this symbol (alphabetically)")
    parser.add_argument("--limit", type=int, help="Limit number of stocks to scrape")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    parser.add_argument("--output", default="scraped_financial_data.json", help="Output JSON file")
    args = parser.parse_args()

    asyncio.run(scrape_all(
        start_from=args.start_from,
        limit=args.limit,
        delay=args.delay,
        output_file=args.output
    ))


if __name__ == "__main__":
    main()
