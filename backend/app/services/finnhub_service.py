"""Finnhub API service for fetching US stock data."""
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# Symbols with known Finnhub EPS data quality issues
# These stocks will use yfinance EPS instead of Finnhub
FINNHUB_EPS_PROBLEM_SYMBOLS = {
    "V",  # Visa - Finnhub reports EPS with wrong share count (6-8x too high)
}

# Hardcoded EPS values for problem stocks (fallback when yfinance fails on Railway)
# Source: Yahoo Finance income statement (Basic EPS)
HARDCODED_EPS_OVERRIDES = {
    "V": {
        2025: 10.22,
        2024: 9.74,
        2023: 8.29,
        2022: 7.01,
        2021: 5.63,
        2020: 4.89,
        2019: 5.32,
        2018: 4.42,
        2017: 2.80,
        2016: 2.84,
        2015: 2.62,
        2014: 2.16,
    },
}


def get_stock_splits(symbol: str) -> List[Dict]:
    """
    Fetch stock split history from yfinance.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        List of splits with date and ratio
    """
    try:
        import yfinance as yf
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
        logger.warning(f"Failed to fetch splits for {symbol}: {e}")
        return []


def calculate_split_adjustment_factor(splits: List[Dict], for_year: int) -> float:
    """
    Calculate cumulative split adjustment factor for a given year.

    If a stock had a 7:1 split in 2014 and 4:1 in 2020:
    - For data from 2013 (before both splits): factor = 7 * 4 = 28
    - For data from 2015 (after first split, before second): factor = 4
    - For data from 2021 (after both splits): factor = 1

    The EPS should be divided by this factor to get split-adjusted values.

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

        # If the data year is before the split year, we need to adjust
        if for_year < split_year and ratio > 1:
            factor *= ratio

    return factor


def apply_split_adjustment(financials_by_year: Dict[int, Dict], symbol: str) -> Dict[int, Dict]:
    """
    Apply split adjustment to EPS values in financial data.

    Args:
        financials_by_year: Financial data keyed by year
        symbol: Stock symbol

    Returns:
        Financial data with split-adjusted EPS
    """
    splits = get_stock_splits(symbol)

    if not splits:
        return financials_by_year

    for year, data in financials_by_year.items():
        factor = calculate_split_adjustment_factor(splits, year)

        if factor > 1:
            # Adjust EPS
            if "eps" in data and data["eps"] is not None:
                original_eps = data["eps"]
                data["eps"] = round(original_eps / factor, 4)
                logger.debug(f"{symbol} {year}: EPS adjusted from {original_eps} to {data['eps']} (factor: {factor})")

            # Adjust diluted EPS if present
            if "eps_diluted" in data and data["eps_diluted"] is not None:
                data["eps_diluted"] = round(data["eps_diluted"] / factor, 4)

    return financials_by_year


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


def _get_yfinance_debt(symbol: str) -> Optional[Dict[int, float]]:
    """
    Fallback to get total debt by year from yfinance when Finnhub doesn't have it.

    Args:
        symbol: Stock symbol

    Returns:
        Dict mapping year to total_debt, or None if failed
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        bs = ticker.balance_sheet

        if bs is None or bs.empty:
            return None

        # Look for Total Debt in balance sheet
        if "Total Debt" not in bs.index:
            return None

        debt_series = bs.loc["Total Debt"]
        result = {}

        for date, value in debt_series.items():
            if value is not None and not (hasattr(value, '__float__') and value != value):  # Check for NaN
                year = date.year
                result[year] = float(value)

        if result:
            logger.info(f"yfinance debt fallback for {symbol}: found {len(result)} years")
        return result if result else None

    except Exception as e:
        logger.warning(f"yfinance debt fallback failed for {symbol}: {e}")
        return None


def _get_yfinance_current_liabilities(symbol: str) -> Optional[Dict[int, float]]:
    """
    Fallback to get current liabilities by year from yfinance when Finnhub doesn't have it.

    Args:
        symbol: Stock symbol

    Returns:
        Dict mapping year to current_liabilities, or None if failed
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        bs = ticker.balance_sheet

        if bs is None or bs.empty:
            return None

        # Look for Current Liabilities in balance sheet
        if "Current Liabilities" not in bs.index:
            return None

        cl_series = bs.loc["Current Liabilities"]
        result = {}

        for date, value in cl_series.items():
            if value is not None and not (hasattr(value, '__float__') and value != value):  # Check for NaN
                year = date.year
                result[year] = float(value)

        if result:
            logger.info(f"yfinance current_liabilities fallback for {symbol}: found {len(result)} years")
        return result if result else None

    except Exception as e:
        logger.warning(f"yfinance current_liabilities fallback failed for {symbol}: {e}")
        return None


def _get_yfinance_eps(symbol: str) -> Optional[Dict[int, float]]:
    """
    Get EPS by year from yfinance. Used for stocks with known Finnhub data issues.

    Args:
        symbol: Stock symbol

    Returns:
        Dict mapping year to EPS, or None if failed
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        income = ticker.income_stmt

        if income is None or income.empty:
            return None

        # Look for Basic EPS (preferred) or Diluted EPS
        eps_key = None
        if "Basic EPS" in income.index:
            eps_key = "Basic EPS"
        elif "Diluted EPS" in income.index:
            eps_key = "Diluted EPS"
        else:
            return None

        eps_series = income.loc[eps_key]
        result = {}

        for date, value in eps_series.items():
            if value is not None and not (hasattr(value, '__float__') and value != value):  # Check for NaN
                year = date.year
                result[year] = float(value)

        if result:
            logger.info(f"yfinance EPS for {symbol}: found {len(result)} years - {result}")
        return result if result else None

    except Exception as e:
        logger.warning(f"yfinance EPS failed for {symbol}: {e}")
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


# GAAP concept mappings for SEC filings (Finnhub uses underscores, not colons)
GAAP_MAPPINGS = {
    # Revenue variants
    "us-gaap_Revenues": "revenue",
    "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "us-gaap_SalesRevenueNet": "revenue",
    "us-gaap_RevenueFromContractWithCustomerIncludingAssessedTax": "revenue",
    "us-gaap_TotalRevenuesAndOtherIncome": "revenue",

    # Net Income
    "us-gaap_NetIncomeLoss": "net_income",
    "us-gaap_ProfitLoss": "net_income",
    "us-gaap_NetIncomeLossAttributableToParent": "net_income",

    # EPS
    "us-gaap_EarningsPerShareBasic": "eps",
    "us-gaap_EarningsPerShareDiluted": "eps_diluted",

    # Equity
    "us-gaap_StockholdersEquity": "total_equity",
    "us-gaap_StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "total_equity",

    # Assets & Liabilities
    "us-gaap_Assets": "total_assets",
    "us-gaap_Liabilities": "total_liabilities",
    "us-gaap_LiabilitiesCurrent": "current_liabilities",
    "us-gaap_LiabilitiesAndStockholdersEquity": "total_assets_check",

    # Debt
    "us-gaap_LongTermDebt": "total_debt",
    "us-gaap_LongTermDebtNoncurrent": "total_debt",
    "us-gaap_DebtInstrumentCarryingAmount": "total_debt",

    # Cash Flow
    "us-gaap_NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "us-gaap_NetCashProvidedByUsedInOperatingActivitiesContinuingOperations": "operating_cash_flow",

    # CapEx
    "us-gaap_PaymentsToAcquirePropertyPlantAndEquipment": "capital_expenditure",
    "us-gaap_PaymentsToAcquireProductiveAssets": "capital_expenditure",

    # Gross Profit
    "us-gaap_GrossProfit": "gross_profit",

    # Operating Income
    "us-gaap_OperatingIncomeLoss": "operating_income",
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

        # Apply stock split adjustment to EPS values
        financials_by_year = apply_split_adjustment(financials_by_year, symbol)

        # Check if any years are missing debt data - use yfinance fallback
        years_missing_debt = [
            year for year, data in financials_by_year.items()
            if data.get("total_debt") is None
        ]

        if years_missing_debt:
            yf_debt = _get_yfinance_debt(symbol)
            if yf_debt:
                for year in years_missing_debt:
                    if year in yf_debt:
                        financials_by_year[year]["total_debt"] = yf_debt[year]
                        logger.debug(f"{symbol} {year}: debt filled from yfinance: {yf_debt[year]}")

        # Check if any years are missing current_liabilities - use yfinance fallback
        years_missing_cl = [
            year for year, data in financials_by_year.items()
            if data.get("current_liabilities") is None
        ]

        if years_missing_cl:
            yf_cl = _get_yfinance_current_liabilities(symbol)
            if yf_cl:
                for year in years_missing_cl:
                    if year in yf_cl:
                        financials_by_year[year]["current_liabilities"] = yf_cl[year]
                        logger.debug(f"{symbol} {year}: current_liabilities filled from yfinance: {yf_cl[year]}")

        # For symbols with known Finnhub EPS data quality issues, override with correct EPS
        if symbol in FINNHUB_EPS_PROBLEM_SYMBOLS:
            logger.info(f"{symbol} is in FINNHUB_EPS_PROBLEM_SYMBOLS - overriding EPS")

            # Try yfinance first
            yf_eps = _get_yfinance_eps(symbol)

            # Fallback to hardcoded values if yfinance fails (common on Railway due to rate limits)
            if not yf_eps and symbol in HARDCODED_EPS_OVERRIDES:
                logger.info(f"{symbol}: yfinance failed, using hardcoded EPS values")
                yf_eps = HARDCODED_EPS_OVERRIDES[symbol]

            if yf_eps:
                for year, eps_value in yf_eps.items():
                    if year in financials_by_year:
                        old_eps = financials_by_year[year].get("eps")
                        financials_by_year[year]["eps"] = eps_value
                        logger.info(f"{symbol} {year}: EPS overridden from {old_eps} to {eps_value}")

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
