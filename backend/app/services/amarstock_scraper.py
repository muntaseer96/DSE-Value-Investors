"""
Amarstock.com scraper for financial data.
Cleaner alternative to LankaBD for revenue, EPS, and net income.
"""
import asyncio
import re
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser


class AmarstockScraper:
    """Scrapes financial data from amarstock.com"""

    BASE_URL = "https://www.amarstock.com/stock"

    # Field mappings from amarstock.com to our database schema
    FIELD_MAPPING = {
        # Revenue fields
        "Revenue": "revenue",  # GP
        "Revenue/ Net Turnover": "revenue",
        "Revenue/ Sales/ Turnover": "revenue",  # OLYMPIC
        "Net Sales Revenue": "revenue",  # BXPHARMA
        "Turnover": "revenue",
        "Interest income": "revenue",  # Banks
        "Total operating income": "revenue",  # Alternative for banks

        # Net Income fields
        "Net Profit after Tax (NPAT) for the year": "net_income",
        "Profit after Tax for the Period": "net_income",
        "Net profit after tax for the year": "net_income",  # Banks
        "Net Profit After Tax": "net_income",
        "Profit / (loss) for the Period": "net_income",  # GP, HEIDELBCEM
        "Profit/ (loss) for the Period": "net_income",
        "Profit/(loss) for the Period": "net_income",
        "NET PROFIT/(LOSS) AFTER TAX": "net_income",  # OLYMPIC
        "Net Profit/(Loss) After Tax": "net_income",
        "Net profit/(loss) after tax": "net_income",
        "Profit for the year": "net_income",  # Common variation
        "Profit for the Year": "net_income",
        "Profit/ (Loss) for the year": "net_income",
        "Profit/(Loss) for the year": "net_income",
        "Net Profit after Income tax": "net_income",  # AAMRANET, IT companies
        "Net Profit after income tax": "net_income",
        "Net profit after Income Tax": "net_income",

        # EPS fields
        "Earnings Per Share (EPS)": "eps",
        "Earnings Per Share (Basic)": "eps",
        "Basic Earnings Per Share (EPS)": "eps",  # OLYMPIC
        "Earnings Per Share": "eps",
        "Earnings Per Share - Basic": "eps",  # HEIDELBCEM
        "EPS": "eps",
        "Earning per Share after Tax": "eps",  # Non-Life Insurance companies

        # Gross Profit
        "Gross Profit": "gross_profit",
        "Net interest income": "gross_profit",  # Banks

        # Operating Income
        "Profit from Operations": "operating_income",
        "Profit/ (Loss) from Operation": "operating_income",  # Common variation
        "Profit/(Loss) from Operation": "operating_income",
        "Operating Profit": "operating_income",  # Banks
        "Operating Income before Financial Expenses": "operating_income",  # Ceramics
        "Income from operation": "operating_income",  # Utilities, Oil companies
        "Net Profit/ (loss) before Financial Expenses": "operating_income",  # Some textiles
        "Net Profit/(loss) before Financial Expenses": "operating_income",
        "Profit before provision against loans and advances": "operating_income",  # NBFIs
    }

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()

    def _parse_number(self, text: str) -> Optional[float]:
        """Parse number from text, handling commas and negative values."""
        if not text:
            return None

        # Clean the text
        text = text.strip()
        if not text or text == '-' or text == '':
            return None

        # Check for negative
        is_negative = text.startswith('-') or text.startswith('(')

        # Remove commas, parentheses, and other non-numeric chars except decimal point
        cleaned = re.sub(r'[^\d.]', '', text)

        if not cleaned:
            return None

        try:
            value = float(cleaned)
            return -value if is_negative else value
        except ValueError:
            return None

    def _get_field_mapping(self, field_name: str) -> Optional[str]:
        """Map amarstock field name to our database field."""
        field_clean = field_name.strip()

        # Exact match first
        if field_clean in self.FIELD_MAPPING:
            return self.FIELD_MAPPING[field_clean]

        # Case-insensitive partial match
        field_lower = field_clean.lower()
        for key, value in self.FIELD_MAPPING.items():
            if key.lower() in field_lower or field_lower in key.lower():
                return value

        return None

    async def scrape_stock(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Scrape financial data for a stock from amarstock.com.

        Returns:
            Dict with 'symbol' and 'years' containing yearly financial data
        """
        url = f"{self.BASE_URL}/{symbol}"

        try:
            # Navigate to stock page
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await self.page.wait_for_timeout(1000)

            # Click on "Company Details" tab
            company_details = self.page.locator('text=Company Details').first
            if await company_details.count() > 0:
                await company_details.click()
                await self.page.wait_for_timeout(1000)
            else:
                print(f"No Company Details tab for {symbol}")
                return None

            # Click on "PROFIT & LOSS" tab
            profit_loss = self.page.locator('text=PROFIT & LOSS').first
            if await profit_loss.count() > 0:
                await profit_loss.click()
                await self.page.wait_for_timeout(1500)
            else:
                print(f"No PROFIT & LOSS tab for {symbol}")
                return None

            # Use JavaScript to extract table data directly
            table_data = await self.page.evaluate('''() => {
                // Find the income statement table - look for table with Revenue and EPS
                const tables = document.querySelectorAll('table');

                for (const table of tables) {
                    const tableText = table.textContent;
                    const tableTextLower = tableText.toLowerCase();

                    // Must have Revenue/Sales/Interest income and EPS (case-insensitive)
                    const hasRevenue = tableTextLower.includes('revenue') || tableTextLower.includes('turnover') ||
                                       tableTextLower.includes('sales') || tableTextLower.includes('interest income') ||
                                       tableTextLower.includes('operating income') || tableTextLower.includes('gross premium');
                    const hasEPS = tableText.includes('EPS') || tableTextLower.includes('earnings per share') ||
                                   tableTextLower.includes('earning per share');

                    if (!hasRevenue || !hasEPS) continue;

                    const rows = table.querySelectorAll('tr');
                    if (rows.length < 5) continue;

                    // First row should have year headers
                    const firstRow = rows[0];
                    const headerCells = Array.from(firstRow.querySelectorAll('th, td'));

                    // Find year columns
                    const yearColumns = {};
                    headerCells.forEach((cell, i) => {
                        const text = cell.textContent.trim();
                        const match = text.match(/^20\\d{2}$/);
                        if (match) {
                            yearColumns[i] = parseInt(text);
                        }
                    });

                    // Need at least 2 years
                    if (Object.keys(yearColumns).length < 2) continue;

                    // Extract all row data
                    const data = [];
                    for (let i = 1; i < rows.length; i++) {
                        const cells = Array.from(rows[i].querySelectorAll('td, th')).map(c => c.textContent.trim());
                        if (cells.length > 1 && cells[0].length > 0) {
                            data.push(cells);
                        }
                    }

                    if (data.length > 3) {
                        return { yearColumns, data };
                    }
                }
                return null;
            }''')

            if not table_data:
                print(f"No table data found for {symbol}")
                return None

            year_columns = {int(k): v for k, v in table_data['yearColumns'].items()}
            rows_data = table_data['data']

            if not year_columns:
                print(f"No year columns found for {symbol}")
                return None

            # Initialize year data
            years_data = {year: {'year': year} for year in year_columns.values()}

            # Parse each row
            for cells in rows_data:
                if len(cells) < 2:
                    continue

                # First cell is usually the field name
                field_name = cells[0].strip() if cells else ''
                db_field = self._get_field_mapping(field_name)

                if db_field:
                    # Get values for each year column
                    for col_idx, year in year_columns.items():
                        if col_idx < len(cells):
                            value = self._parse_number(cells[col_idx])
                            if value is not None:
                                years_data[year][db_field] = value

            # Convert to list format
            years_list = [data for data in years_data.values() if len(data) > 1]

            return {
                'symbol': symbol,
                'years': sorted(years_list, key=lambda x: x['year'])
            }

        except Exception as e:
            print(f"Error scraping {symbol}: {e}")
            return None

    async def scrape_multiple(self, symbols: List[str], delay: float = 2.0) -> List[Dict[str, Any]]:
        """Scrape multiple stocks with delay between requests."""
        results = []
        for i, symbol in enumerate(symbols):
            result = await self.scrape_stock(symbol)
            if result:
                results.append(result)

            # Delay between requests to avoid rate limiting
            if i < len(symbols) - 1:
                await asyncio.sleep(delay)

        return results


async def test_scraper():
    """Test the scraper with a few stocks."""
    test_symbols = ['BXPHARMA', 'BANKASIA', 'BRACBANK']

    async with AmarstockScraper() as scraper:
        for symbol in test_symbols:
            print(f"\n=== {symbol} ===")
            result = await scraper.scrape_stock(symbol)

            if result and result.get('years'):
                for year_data in result['years']:
                    year = year_data.get('year')
                    rev = year_data.get('revenue')
                    eps = year_data.get('eps')
                    net = year_data.get('net_income')
                    print(f"  {year}: revenue={rev}, eps={eps}, net_income={net}")
            else:
                print("  No data found")

            await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(test_scraper())
