#!/usr/bin/env python3
"""
Scrape equity data in batches and output SQL for database updates.

Usage:
    python3 scripts/scrape_equity_batch.py --symbols SUMITPOWER,CVOPRL,GP
    python3 scripts/scrape_equity_batch.py --file symbols.txt
    python3 scripts/scrape_equity_batch.py --batch 1  # Process batch 1 of missing stocks
"""
import asyncio
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.lankabd_scraper import LankaBDScraper

# All stocks with missing equity data (from database query)
MISSING_EQUITY_STOCKS = [
    "AAMRANET", "AAMRATECH", "ADNTEL", "AFTABAUTO", "AGNISYSL", "AGRANINS",
    "AMANFEED", "ANWARGALV", "AOL", "APOLOISPAT", "ARAMIT", "ARAMITCEM",
    "ASIAINS", "ATLASBANG", "AZIZPIPES", "BARKAPOWER", "BBS", "BBSCABLES",
    "BDAUTOCA", "BDCOM", "BDLAMPS", "BDSERVICE", "BDTHAI", "BDWELDING",
    "BENGALWTL", "BERGERPBL", "BESTHLDNG", "BEXIMCO", "BPML", "BPPL", "BSC",
    "BSCPLC", "CLICL", "CONFIDCEM", "COPPERTECH", "CROWNCEMNT", "CVOPRL",
    "DAFODILCOM", "DELTALIFE", "DESCO", "DESHBANDHU", "DOMINAGE", "EASTRNLUB",
    "ECABLES", "EGEN", "EHL", "EPGL", "FAREASTLIF", "GBBPOWER", "GENEXIL",
    "GOLDENSON", "GP", "GPHISPAT", "GQBALLPEN", "HAKKANIPUL", "HEIDELBCEM",
    "IFADAUTOS", "INDEXAGRO", "INTECH", "INTRACO", "ISNLTD", "ITC",
    "JAMUNAOIL", "KAY&QUE", "KBPPWBIL", "KDSALTD", "KPCL", "KPPL", "LHB",
    "LINDEBD", "LRBDL", "MAGURAPLEX", "MEGHNACEM", "MEGHNALIFE", "MIRACLEIND",
    "MIRAKHTER", "MONNOAGML", "MONOSPOOL", "MPETROLEUM", "NAHEEACP",
    "NATLIFEINS", "NAVANACNG", "NFML", "NPOLYMER", "NTLTUBES", "OAL", "OIMEX",
    "PADMALIFE", "PADMAOIL", "PARAMOUNT", "PENINSULA", "POPULARLIF",
    "POWERGRID", "PRAGATILIF", "PREMIERCEM", "PRIMELIFE", "PROGRESLIF",
    "QUASEMIND", "RANFOUNDRY", "RENWICKJA", "ROBI", "RSRMSTEEL", "RUNNERAUTO",
    "RUPALILIFE", "SAIFPOWER", "SALAMCRST", "SAMORITA", "SANDHANINS",
    "SAPORTL", "SAVAREFR", "SEAPEARL", "SHURWID", "SINGERBD", "SINOBANGLA",
    "SKTRIMS", "SONALILIFE", "SONALIPAPR", "SPCL", "SSSTEEL", "SUMITPOWER",
    "SUNLIFEINS", "TILIL", "TITASGAS", "UNIQUEHRL", "UPGDCL", "USMANIAGL",
    "WALTONHIL", "WMSHIPYARD", "YPL"
]


async def scrape_batch(symbols, output_format='json'):
    """Scrape a batch of stocks and output results."""
    results = []

    async with LankaBDScraper() as scraper:
        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] Scraping {symbol}...", end=" ", flush=True)

            try:
                result = await scraper.scrape_stock(symbol)

                if result['success'] and result.get('data'):
                    data = result['data']
                    equity_count = sum(1 for d in data if d.get('total_equity'))
                    print(f"OK - {equity_count}/{len(data)} years with equity")

                    for year_data in data:
                        if year_data.get('total_equity'):
                            results.append({
                                'symbol': symbol,
                                'year': year_data['year'],
                                'total_equity': year_data['total_equity']
                            })
                else:
                    print(f"FAILED - {result.get('error', 'Unknown')}")

            except Exception as e:
                print(f"ERROR - {e}")

            if i < len(symbols) - 1:
                await asyncio.sleep(2)

    return results


def output_sql(results):
    """Output SQL UPDATE statements."""
    print("\n" + "="*60)
    print("SQL UPDATE STATEMENTS")
    print("="*60 + "\n")

    for r in results:
        print(f"UPDATE financial_data SET total_equity = {r['total_equity']} "
              f"WHERE stock_symbol = '{r['symbol']}' AND year = {r['year']};")


def output_json(results):
    """Output JSON data."""
    print("\n" + "="*60)
    print("JSON DATA")
    print("="*60 + "\n")
    print(json.dumps(results, indent=2))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", help="Comma-separated stock symbols")
    parser.add_argument("--batch", type=int, help="Batch number (1-based, 5 stocks each)")
    parser.add_argument("--format", choices=['json', 'sql'], default='json')
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    elif args.batch:
        batch_size = 5
        start = (args.batch - 1) * batch_size
        end = start + batch_size
        symbols = MISSING_EQUITY_STOCKS[start:end]
        total_batches = (len(MISSING_EQUITY_STOCKS) + batch_size - 1) // batch_size
        print(f"Batch {args.batch}/{total_batches}: {symbols}")
    else:
        print("Please specify --symbols or --batch")
        return

    results = await scrape_batch(symbols)

    if args.format == 'sql':
        output_sql(results)
    else:
        output_json(results)

    print(f"\nTotal records: {len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
