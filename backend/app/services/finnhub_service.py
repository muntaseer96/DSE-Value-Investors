"""Finnhub API service for fetching US stock data.

Simplified version - only handles:
- Symbol list fetching (for seeding)
- Live price quotes (with yfinance fallback)
- Company profiles
- Basic metrics (52w high/low)

Financial data now comes from SimFin bulk import.
"""
import asyncio
import time
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


def _get_yfinance_quote(symbol: str) -> Optional[Dict]:
    """
    Fallback to get quote from yfinance when Finnhub doesn't have data.

    Args:
        symbol: Stock symbol

    Returns:
        Quote dict or None if failed
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            return None

        current_price = info.get("regularMarketPrice")
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        if not current_price:
            return None

        change = None
        change_pct = None
        if current_price and previous_close:
            change = current_price - previous_close
            change_pct = (change / previous_close) * 100 if previous_close else None

        return {
            "current_price": current_price,
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "high": info.get("dayHigh"),
            "low": info.get("dayLow"),
            "open": info.get("open") or info.get("regularMarketOpen"),
        }
    except Exception as e:
        logger.warning(f"yfinance fallback failed for {symbol}: {e}")
        return None


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


class FinnhubService:
    """Service for fetching US stock data from Finnhub API.

    Now only used for:
    - Fetching all US stock symbols (seeding)
    - Live price quotes
    - Company profiles and basic metrics

    Financial data (revenue, EPS, etc.) comes from SimFin.
    """

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
        result = {
            "current_price": data.get("c"),  # Current price
            "previous_close": data.get("pc"),  # Previous close
            "change": data.get("d"),  # Change
            "change_pct": data.get("dp"),  # Change percent
            "high": data.get("h"),  # Day high
            "low": data.get("l"),  # Day low
            "open": data.get("o"),  # Open price
            "timestamp": data.get("t"),  # Timestamp
        }

        # If Finnhub returns 0 or None for price, try yfinance as fallback
        if not result["current_price"]:
            yf_quote = _get_yfinance_quote(symbol)
            if yf_quote:
                result.update(yf_quote)
                logger.info(f"Used yfinance fallback for {symbol} quote")

        return result

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
        Fetch basic financial metrics (52w high/low, etc.).

        Note: Detailed financials now come from SimFin.

        Args:
            symbol: Stock symbol

        Returns:
            Financial metrics including 52-week high/low
        """
        data = await self._request("stock/metric", {"symbol": symbol, "metric": "all"})

        metric = data.get("metric", {})
        return {
            "high_52w": metric.get("52WeekHigh"),
            "low_52w": metric.get("52WeekLow"),
            "pe_ratio": metric.get("peTTM"),
            "pb_ratio": metric.get("pbQuarterly"),
            "eps_ttm": metric.get("epsTTM"),
        }


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
