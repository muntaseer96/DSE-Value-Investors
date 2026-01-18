"""LankaBD Financial Data Scraper.

Autonomous scraper for lankabd.com to fetch comprehensive financial statement data
(Balance Sheet, Income Statement, Cash Flow) for DSE stocks.

This data is needed for Phil Town valuation (Big Five, Sticker Price) but is not
available from the stocksurferbd API.

Frequency: Run once per year after annual reports are published (typically Q1)
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class LankaBDScraper:
    """Autonomous scraper for lankabd.com financial data using Playwright."""

    BASE_URL = "https://www.lankabd.com"

    # Field mappings from LankaBD to our database schema
    FIELD_MAPPING = {
        # Balance Sheet
        "TOTAL ASSETS": "total_assets",
        "Total Shareholders' Equity": "total_equity",
        "Shareholders' Equity:": "total_equity",
        "Shareholders' Equity": "total_equity",
        "Total Shareloders' Equity": "total_equity",  # typo on BPML, HAKKANIPUL
        "Equity attributable to the Company's equity holders": "total_equity",  # BSC
        "Equity attributable to the Company's equity holders:": "total_equity",  # BSC with colon
        "Equity attributable to the Company\"s equity holders": "total_equity",  # BSC variant
        "Equity attributable to the Company\"s equity holders:": "total_equity",  # BSC variant with colon
        "Equity attributable to": "total_equity",  # partial match fallback
        # Simple "Total Equity" variations (GP, ROBI, TITASGAS, UPGDCL, CROWNCEMNT)
        "Total Equity": "total_equity",
        "Total EQUITY": "total_equity",
        "Total equity": "total_equity",
        "SHAREHOLDERS\" EQUITY- PARENT COMPANY": "total_equity",  # CROWNCEMNT
        "Total Non-Current Liabilities": "non_current_liabilities",
        "Non-Current Liabilities:": "non_current_liabilities",
        "Non-Current Liabilities": "non_current_liabilities",
        "Total Current Liabilities": "current_liabilities",
        "Current Liabilities:": "current_liabilities",
        "Current Liabilities": "current_liabilities",
        # Income Statement - Revenue variations
        "Net Sales Revenue": "revenue",
        "Revenue": "revenue",
        "Collection from revenue": "revenue",
        "Net Turnover": "revenue",  # BPML, HAKKANIPUL
        "Revenue/ Net Turnover": "revenue",  # BSC
        "Turnover": "revenue",
        # Income Statement - Profit
        "Gross Profit": "gross_profit",
        "Profit from Operations": "operating_income",
        "Profit from Operation": "operating_income",
        "Operating Profit": "operating_income",
        "Profit after Tax for the Period": "net_income",
        "Net Profit After Tax": "net_income",
        "Net profit/ (Loss) after tax": "net_income",  # BPML, HAKKANIPUL
        "Net Profit after Tax (NPAT) for the year": "net_income",  # BSC
        "Net profit/(Loss) after tax": "net_income",
        "Profit Before Tax": "profit_before_tax",
        "Net Profit Before Tax": "profit_before_tax",
        # Income Statement - EPS variations
        "Earnings Per Share (EPS)": "eps",
        "Basic Earnings Per Share": "eps",
        "Earnings per share (Fully diluted basis)": "eps",  # BPML, HAKKANIPUL
        "Earnings Per Share (Basic)": "eps",  # BSC
        "EPS": "eps",
        "Earnings Per Share": "eps",
        # Cash Flow - multiple variations across different companies
        "Net cash flows from operating activities": "operating_cash_flow",
        "Net cash from operating activities": "operating_cash_flow",
        "Cash flows from operating activities": "operating_cash_flow",
        "Cash generated from operating activities": "operating_cash_flow",
        "Net cash generated from /(used in) operating activities": "operating_cash_flow",
        "Net cash generated from/(used in) operating activities": "operating_cash_flow",
        "Net Cash Generated from Operating Activities": "operating_cash_flow",
        "Net Cash Generated from Operating Actvities": "operating_cash_flow",  # typo on some pages
        "Net cash generated from operating activities": "operating_cash_flow",
        "Cash Generated from Operations": "operating_cash_flow",
        "Net cash inflow from operating activities": "operating_cash_flow",
        "Cash inflow from operating activities": "operating_cash_flow",
        # "provided" variations - common across many companies
        "Net cash provided from operating activities": "operating_cash_flow",
        "Net cash provided by operating activities": "operating_cash_flow",
        "Net Cash Provided/(Used) by Operating Activities": "operating_cash_flow",
        "Net Cash Provided/(Used) by Operation activities": "operating_cash_flow",
        "Net cash provided/(used) by operating activities": "operating_cash_flow",
        "Net cash provided/(used) in operating activities": "operating_cash_flow",
        "Acquisition of property, plant and equipment": "capital_expenditure",
        "Purchase of property, plant and equipment": "capital_expenditure",
        "Acquisition of PPE": "capital_expenditure",
        "Property, plant and equipment acquired": "capital_expenditure",
    }

    def __init__(self):
        self.playwright = None
        self.browser = None
        self._is_initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize Playwright browser."""
        if self._is_initialized:
            return

        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self._is_initialized = True
            logger.info("LankaBD scraper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise RuntimeError(
                "Failed to initialize browser. Make sure Playwright is installed: "
                "pip install playwright && playwright install chromium"
            ) from e

    async def close(self):
        """Close browser and Playwright."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self._is_initialized = False

    async def scrape_stock(self, symbol: str) -> Dict[str, Any]:
        """Scrape all financial data for one stock.

        Args:
            symbol: Stock symbol (e.g., 'OLYMPIC', 'BEXIMCO')

        Returns:
            Dict with success status and data/error
        """
        if not self._is_initialized:
            await self.initialize()

        page = await self.browser.new_page()
        page.set_default_timeout(30000)  # 30 second timeout

        try:
            # Navigate to company search page
            search_url = f"{self.BASE_URL}/Company/Search?searchText={symbol}"
            logger.info(f"Scraping {symbol} from {search_url}")

            await page.goto(search_url)
            await page.wait_for_load_state("networkidle")

            # Check if we found the company
            page_content = await page.content()
            if "No company found" in page_content or "No result" in page_content:
                return {
                    "symbol": symbol,
                    "success": False,
                    "error": f"Company {symbol} not found on LankaBD"
                }

            # Click Financial Statement tab
            try:
                await page.click('a:has-text("FINANCIAL STATEMENT")', timeout=10000)
                await page.wait_for_timeout(2000)  # Wait for tab content to load
            except Exception as e:
                logger.warning(f"Could not find Financial Statement tab for {symbol}: {e}")
                return {
                    "symbol": symbol,
                    "success": False,
                    "error": "Could not find Financial Statement section"
                }

            # Extract data from each sub-tab
            # Need to click each sub-tab to load its content

            # Balance Sheet (usually active by default)
            try:
                await page.click('a[href="#balancesheet"]', timeout=5000)
                await page.wait_for_timeout(1000)
            except:
                pass
            balance_sheet = await self._extract_table_data(page, "#balancesheet")

            # Income Statement
            try:
                await page.click('a[href="#incomeStatement"]', timeout=5000)
                await page.wait_for_timeout(1000)
            except:
                pass
            income_statement = await self._extract_table_data(page, "#incomeStatement")

            # Cash Flow
            try:
                await page.click('a[href="#cashflow"]', timeout=5000)
                await page.wait_for_timeout(1000)
            except:
                pass
            cash_flow = await self._extract_table_data(page, "#cashflow")

            # Merge data by year
            merged_data = self._merge_financial_data(
                balance_sheet,
                income_statement,
                cash_flow
            )

            return {
                "symbol": symbol,
                "success": True,
                "data": merged_data,
                "raw": {
                    "balance_sheet": balance_sheet,
                    "income_statement": income_statement,
                    "cash_flow": cash_flow,
                },
                "scraped_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to scrape {symbol}: {e}")
            return {
                "symbol": symbol,
                "success": False,
                "error": str(e)
            }
        finally:
            await page.close()

    async def _extract_table_data(self, page, panel_selector: str) -> List[Dict[str, Any]]:
        """Extract table data from a specific panel using JavaScript.

        Args:
            page: Playwright page object
            panel_selector: CSS selector for the panel (e.g., '#balancesheet')

        Returns:
            List of dicts with year-wise data
        """
        try:
            # Use JavaScript to extract table data
            data = await page.evaluate(f'''
                () => {{
                    const panel = document.querySelector('{panel_selector}');
                    if (!panel) return null;

                    const table = panel.querySelector('table');
                    if (!table) return null;

                    const rows = Array.from(table.rows);
                    if (rows.length < 2) return null;

                    // Get years from header row (skip first "Particulars" column)
                    const headers = Array.from(rows[0].cells).map(c => c.innerText.trim());
                    const years = headers.slice(1).map(h => {{
                        const match = h.match(/20\\d{{2}}/);
                        return match ? parseInt(match[0]) : null;
                    }}).filter(y => y !== null);

                    // Extract data rows
                    const result = [];
                    for (let i = 1; i < rows.length; i++) {{
                        const cells = Array.from(rows[i].cells);
                        if (cells.length < 2) continue;

                        const fieldName = cells[0].innerText.trim();
                        const values = cells.slice(1).map(c => {{
                            let text = c.innerText.trim();
                            // Remove commas and handle parentheses for negatives
                            text = text.replace(/,/g, '');
                            const isNegative = text.includes('(') && text.includes(')');
                            text = text.replace(/[()]/g, '');
                            const num = parseFloat(text);
                            if (isNaN(num)) return null;
                            return isNegative ? -num : num;
                        }});

                        result.push({{
                            field: fieldName,
                            values: values
                        }});
                    }}

                    return {{
                        years: years,
                        rows: result
                    }};
                }}
            ''')

            if not data or not data.get('years') or not data.get('rows'):
                logger.warning(f"No data found in panel {panel_selector}")
                return []

            # Transform into year-wise records
            years = data['years']
            records = {year: {'year': year} for year in years}

            for row in data['rows']:
                field_name = row['field']
                values = row['values']

                # Map field name to our schema
                db_field = self._get_field_mapping(field_name)
                if not db_field:
                    continue

                # Assign values to each year
                for i, year in enumerate(years):
                    if i < len(values) and values[i] is not None:
                        records[year][db_field] = values[i]

            return [records[year] for year in sorted(records.keys())]

        except Exception as e:
            logger.error(f"Error extracting table from {panel_selector}: {e}")
            return []

    def _get_field_mapping(self, field_name: str) -> Optional[str]:
        """Get database field name for a LankaBD field.

        Args:
            field_name: Field name from LankaBD

        Returns:
            Database field name or None
        """
        field_name_clean = field_name.strip()

        # Try exact match
        if field_name_clean in self.FIELD_MAPPING:
            return self.FIELD_MAPPING[field_name_clean]

        # Try case-insensitive partial match
        field_lower = field_name_clean.lower()
        for key, value in self.FIELD_MAPPING.items():
            if key.lower() in field_lower or field_lower in key.lower():
                return value

        return None

    def _merge_financial_data(
        self,
        balance_sheet: List[Dict],
        income_statement: List[Dict],
        cash_flow: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Merge data from all three financial statements by year.

        Args:
            balance_sheet: Balance sheet data
            income_statement: Income statement data
            cash_flow: Cash flow data

        Returns:
            Merged list sorted by year
        """
        merged = {}

        for data_list in [balance_sheet, income_statement, cash_flow]:
            for record in data_list:
                year = record.get('year')
                if year:
                    if year not in merged:
                        merged[year] = {'year': year}
                    for key, value in record.items():
                        if key != 'year' and value is not None:
                            merged[year][key] = value

        # Calculate total_debt from liabilities if not present
        for year_data in merged.values():
            if 'total_debt' not in year_data:
                non_current = year_data.get('non_current_liabilities', 0) or 0
                current = year_data.get('current_liabilities', 0) or 0
                if non_current or current:
                    year_data['total_debt'] = non_current + current

            # Calculate free_cash_flow if we have OCF and CapEx
            if 'operating_cash_flow' in year_data and 'capital_expenditure' in year_data:
                ocf = year_data['operating_cash_flow'] or 0
                capex = year_data['capital_expenditure'] or 0
                year_data['free_cash_flow'] = ocf - abs(capex)

        # Sort by year (oldest first)
        return [merged[year] for year in sorted(merged.keys())]

    async def scrape_batch(
        self,
        symbols: List[str],
        delay: float = 2.0,
        progress_callback: Optional[Callable[[int, int, str, bool], None]] = None
    ) -> Dict[str, Any]:
        """Batch scrape multiple stocks autonomously.

        Args:
            symbols: List of stock symbols
            delay: Delay between requests in seconds (rate limiting)
            progress_callback: Optional callback(current, total, symbol, success)

        Returns:
            Dict with success and failed lists
        """
        results = {
            "success": [],
            "failed": [],
            "started_at": datetime.now().isoformat(),
        }

        total = len(symbols)

        for i, symbol in enumerate(symbols):
            result = await self.scrape_stock(symbol)

            if result["success"]:
                results["success"].append(result)
            else:
                results["failed"].append(result)

            if progress_callback:
                progress_callback(i + 1, total, symbol, result["success"])

            # Rate limiting - wait between requests
            if i < total - 1:
                await asyncio.sleep(delay)

        results["completed_at"] = datetime.now().isoformat()
        results["total"] = total
        results["success_count"] = len(results["success"])
        results["failed_count"] = len(results["failed"])

        return results


# Synchronous wrapper for non-async contexts
class LankaBDScraperSync:
    """Synchronous wrapper for LankaBDScraper."""

    def __init__(self):
        self._scraper = LankaBDScraper()

    def __enter__(self):
        asyncio.get_event_loop().run_until_complete(self._scraper.initialize())
        return self

    def __exit__(self, *args):
        asyncio.get_event_loop().run_until_complete(self._scraper.close())

    def scrape_stock(self, symbol: str) -> Dict[str, Any]:
        """Scrape single stock synchronously."""
        return asyncio.get_event_loop().run_until_complete(
            self._scraper.scrape_stock(symbol)
        )

    def scrape_batch(
        self,
        symbols: List[str],
        delay: float = 2.0,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Batch scrape synchronously."""
        return asyncio.get_event_loop().run_until_complete(
            self._scraper.scrape_batch(symbols, delay, progress_callback)
        )


async def scrape_single_stock(symbol: str) -> Dict[str, Any]:
    """Convenience function to scrape a single stock.

    Args:
        symbol: Stock symbol

    Returns:
        Scrape result dict
    """
    async with LankaBDScraper() as scraper:
        return await scraper.scrape_stock(symbol)


async def scrape_all_stocks(
    symbols: List[str],
    delay: float = 2.0,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Convenience function to scrape multiple stocks.

    Args:
        symbols: List of stock symbols
        delay: Rate limiting delay
        progress_callback: Progress callback function

    Returns:
        Batch result dict
    """
    async with LankaBDScraper() as scraper:
        return await scraper.scrape_batch(symbols, delay, progress_callback)
