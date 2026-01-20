"""Finnhub API service for fetching US stock data."""
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls: int = 60, period: int = 60):
        """
        Initialize rate limiter.

        Args:
            calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.timestamps: List[float] = []

    async def acquire(self):
        """Wait if necessary to stay within rate limit."""
        now = time.time()
        # Remove timestamps older than the period
        self.timestamps = [t for t in self.timestamps if now - t < self.period]

        if len(self.timestamps) >= self.calls:
            # Need to wait
            oldest = self.timestamps[0]
            wait_time = self.period - (now - oldest) + 0.1  # Add small buffer
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self.timestamps.append(time.time())


# GAAP concept mappings for SEC filings
GAAP_MAPPINGS = {
    # Revenue variants
    "us-gaap:Revenues": "revenue",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "us-gaap:SalesRevenueNet": "revenue",
    "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax": "revenue",
    "us-gaap:TotalRevenuesAndOtherIncome": "revenue",

    # Net Income
    "us-gaap:NetIncomeLoss": "net_income",
    "us-gaap:ProfitLoss": "net_income",
    "us-gaap:NetIncomeLossAttributableToParent": "net_income",

    # EPS
    "us-gaap:EarningsPerShareBasic": "eps",
    "us-gaap:EarningsPerShareDiluted": "eps_diluted",

    # Equity
    "us-gaap:StockholdersEquity": "total_equity",
    "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "total_equity",

    # Assets & Liabilities
    "us-gaap:Assets": "total_assets",
    "us-gaap:Liabilities": "total_liabilities",
    "us-gaap:LiabilitiesAndStockholdersEquity": "total_assets_check",

    # Debt
    "us-gaap:LongTermDebt": "total_debt",
    "us-gaap:LongTermDebtNoncurrent": "total_debt",
    "us-gaap:DebtInstrumentCarryingAmount": "total_debt",

    # Cash Flow
    "us-gaap:NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations": "operating_cash_flow",

    # CapEx
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment": "capital_expenditure",
    "us-gaap:PaymentsToAcquireProductiveAssets": "capital_expenditure",

    # Gross Profit
    "us-gaap:GrossProfit": "gross_profit",

    # Operating Income
    "us-gaap:OperatingIncomeLoss": "operating_income",
}


class FinnhubService:
    """Service for fetching US stock data from Finnhub API."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str):
        """
        Initialize Finnhub service.

        Args:
            api_key: Finnhub API key
        """
        self.api_key = api_key
        self.rate_limiter = RateLimiter(calls=60, period=60)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a rate-limited request to Finnhub API.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        if not self._client:
            raise RuntimeError("FinnhubService must be used as async context manager")

        await self.rate_limiter.acquire()

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["token"] = self.api_key

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Finnhub API error for {endpoint}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Finnhub API request failed for {endpoint}: {e}")
            raise

    async def get_all_us_symbols(self) -> List[Dict]:
        """
        Fetch all US stock symbols.

        Returns:
            List of stock symbols with metadata
        """
        data = await self._request("stock/symbol", {"exchange": "US"})
        return data

    async def get_quote(self, symbol: str) -> Dict:
        """
        Fetch current price quote for a symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            Quote data with current price, change, etc.
        """
        data = await self._request("quote", {"symbol": symbol})
        return {
            "current_price": data.get("c"),  # Current price
            "previous_close": data.get("pc"),  # Previous close
            "change": data.get("d"),  # Change
            "change_pct": data.get("dp"),  # Change percent
            "high": data.get("h"),  # Day high
            "low": data.get("l"),  # Day low
            "open": data.get("o"),  # Open price
            "timestamp": data.get("t"),  # Timestamp
        }

    async def get_company_profile(self, symbol: str) -> Dict:
        """
        Fetch company profile.

        Args:
            symbol: Stock symbol

        Returns:
            Company profile with name, sector, market cap, etc.
        """
        data = await self._request("stock/profile2", {"symbol": symbol})
        return {
            "name": data.get("name"),
            "sector": data.get("finnhubIndustry"),
            "market_cap": data.get("marketCapitalization"),  # In millions
            "ipo": data.get("ipo"),
            "country": data.get("country"),
            "exchange": data.get("exchange"),
            "weburl": data.get("weburl"),
        }

    async def get_basic_financials(self, symbol: str) -> Dict:
        """
        Fetch basic financial metrics.

        Args:
            symbol: Stock symbol

        Returns:
            Financial metrics including ratios, 52-week high/low, etc.
        """
        data = await self._request("stock/metric", {"symbol": symbol, "metric": "all"})

        metric = data.get("metric", {})
        return {
            "roe": metric.get("roeTTM"),
            "roa": metric.get("roaTTM"),
            "gross_margin": metric.get("grossMarginTTM"),
            "operating_margin": metric.get("operatingMarginTTM"),
            "net_margin": metric.get("netProfitMarginTTM"),
            "debt_to_equity": metric.get("totalDebt/totalEquityQuarterly"),
            "current_ratio": metric.get("currentRatioQuarterly"),
            "high_52w": metric.get("52WeekHigh"),
            "low_52w": metric.get("52WeekLow"),
            "pe_ratio": metric.get("peTTM"),
            "pb_ratio": metric.get("pbQuarterly"),
            "eps_ttm": metric.get("epsTTM"),
            "book_value_per_share": metric.get("bookValuePerShareQuarterly"),
            "revenue_per_share": metric.get("revenuePerShareTTM"),
        }

    async def get_financials_reported(self, symbol: str, freq: str = "annual") -> Dict:
        """
        Fetch SEC-reported financials.

        Args:
            symbol: Stock symbol
            freq: Frequency ("annual" or "quarterly")

        Returns:
            Parsed financial data by year
        """
        data = await self._request("stock/financials-reported", {
            "symbol": symbol,
            "freq": freq
        })

        reports = data.get("data", [])
        financials_by_year: Dict[int, Dict[str, Any]] = {}

        for report in reports:
            # Get year from filing date or period
            end_date = report.get("endDate", "")
            if end_date:
                try:
                    year = int(end_date.split("-")[0])
                except (ValueError, IndexError):
                    continue
            else:
                continue

            if year not in financials_by_year:
                financials_by_year[year] = {"year": year}

            # Parse report data
            report_data = report.get("report", {})

            # Process balance sheet, income statement, and cash flow
            for section in ["bs", "ic", "cf"]:
                section_data = report_data.get(section, [])
                for item in section_data:
                    concept = item.get("concept", "")
                    value = item.get("value")

                    if value is None:
                        continue

                    # Map GAAP concept to our field
                    field_name = GAAP_MAPPINGS.get(concept)
                    if field_name and field_name not in financials_by_year[year]:
                        try:
                            financials_by_year[year][field_name] = float(value)
                        except (ValueError, TypeError):
                            pass

        return financials_by_year

    async def scrape_stock(self, symbol: str) -> Dict:
        """
        Scrape all available data for a single stock.

        Args:
            symbol: Stock symbol

        Returns:
            Combined data from all endpoints
        """
        result = {
            "symbol": symbol,
            "quote": None,
            "profile": None,
            "metrics": None,
            "financials": None,
            "error": None,
        }

        try:
            # Fetch quote
            result["quote"] = await self.get_quote(symbol)
        except Exception as e:
            logger.warning(f"Failed to get quote for {symbol}: {e}")

        try:
            # Fetch company profile
            result["profile"] = await self.get_company_profile(symbol)
        except Exception as e:
            logger.warning(f"Failed to get profile for {symbol}: {e}")

        try:
            # Fetch basic financials/metrics
            result["metrics"] = await self.get_basic_financials(symbol)
        except Exception as e:
            logger.warning(f"Failed to get metrics for {symbol}: {e}")

        try:
            # Fetch SEC-reported financials
            result["financials"] = await self.get_financials_reported(symbol)
        except Exception as e:
            logger.warning(f"Failed to get financials for {symbol}: {e}")

        return result


# S&P 500 symbols (as of 2024)
SP500_SYMBOLS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AFL",
    "AIG", "AMAT", "AMD", "AMGN", "AMT", "AMZN", "ANET", "ANSS", "AON", "APA",
    "APD", "APH", "APTV", "ARE", "ATO", "AVGO", "AVY", "AXP", "AZO", "BA",
    "BAC", "BAX", "BBY", "BDX", "BEN", "BIIB", "BK", "BKNG", "BLK", "BMY",
    "BR", "BRK.B", "BSX", "BWA", "BXP", "C", "CAG", "CAH", "CAT", "CB",
    "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG", "CF", "CFG",
    "CHD", "CHRW", "CI", "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG",
    "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COST", "CPB", "CPRT",
    "CPT", "CRL", "CRM", "CSCO", "CSGP", "CSX", "CTAS", "CTLT", "CTSH", "CTVA",
    "CVS", "CVX", "CZR", "D", "DAL", "DD", "DE", "DFS", "DG", "DGX",
    "DHI", "DHR", "DIS", "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRI", "DTE",
    "DUK", "DVA", "DVN", "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EIX",
    "EL", "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES",
    "ESS", "ETN", "ETR", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F",
    "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FIS", "FITB", "FLT",
    "FMC", "FOX", "FOXA", "FRC", "FRT", "FTNT", "FTV", "GD", "GE", "GEHC",
    "GEN", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC",
    "GPN", "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "HOLX",
    "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUM", "HWM", "IBM",
    "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH", "IP",
    "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT",
    "JCI", "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC",
    "KIM", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "L", "LDOS", "LEN",
    "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX",
    "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS",
    "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK",
    "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC",
    "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH",
    "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE",
    "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL",
    "NWS", "NWSA", "NXPI", "O", "ODFL", "OGN", "OKE", "OMC", "ON", "ORCL",
    "ORLY", "OTIS", "OXY", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEAK", "PEG",
    "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PKI", "PLD",
    "PM", "PNC", "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX",
    "PTC", "PWR", "PXD", "PYPL", "QCOM", "QRVO", "RCL", "RE", "REG", "REGN",
    "RF", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX",
    "SBAC", "SBUX", "SCHW", "SEE", "SHW", "SIVB", "SJM", "SLB", "SNA", "SNPS",
    "SO", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ", "SWK", "SWKS",
    "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER",
    "TFC", "TFX", "TGT", "TJX", "TMO", "TMUS", "TPR", "TRMB", "TROW", "TRV",
    "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UDR",
    "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VFC", "VICI",
    "VLO", "VMC", "VNO", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ", "WAB",
    "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WM", "WMB",
    "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XRAY",
    "XYL", "YUM", "ZBH", "ZBRA", "ZION", "ZTS"
]
