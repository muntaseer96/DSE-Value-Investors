"""DSE Data Service - Fetches data from stocksurferbd and bdshare.

This service abstracts the data fetching logic and provides clean interfaces
for getting current prices, historical data, and fundamental data.
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DSEDataService:
    """Service for fetching DSE stock data."""

    def __init__(self, data_dir: str = "data"):
        """Initialize the data service.

        Args:
            data_dir: Directory to store downloaded data files
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def get_current_prices(self) -> pd.DataFrame:
        """Get current prices for all DSE stocks.

        Returns:
            DataFrame with columns: symbol, ltp (last trade price), high, low, etc.
        """
        try:
            from bdshare import get_current_trade_data
            df = get_current_trade_data()
            if df is not None and not df.empty:
                # Standardize column names
                df.columns = df.columns.str.lower().str.replace(' ', '_')
                return df
        except Exception as e:
            logger.error(f"Error fetching current prices from bdshare: {e}")

        # Fallback to stocksurferbd
        try:
            from stocksurferbd import PriceData
            file_path = os.path.join(self.data_dir, "current_prices.xlsx")
            PriceData().save_current_data(file_name=file_path, market='DSE')
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            return df
        except Exception as e:
            logger.error(f"Error fetching current prices from stocksurferbd: {e}")

        return pd.DataFrame()

    def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for a specific stock.

        Args:
            symbol: Stock symbol (e.g., "BXPHARMA")

        Returns:
            Dict with price data or None if not found
        """
        try:
            from bdshare import get_current_trade_data
            df = get_current_trade_data(symbol)
            if df is not None and not df.empty:
                df.columns = df.columns.str.lower().str.replace(' ', '_')
                row = df.iloc[0].to_dict()
                return row
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")

        # Try from full list
        try:
            df = self.get_current_prices()
            if not df.empty:
                # Try different column names for symbol
                symbol_col = None
                for col in ['trading_code', 'symbol', 'code', 'ticker']:
                    if col in df.columns:
                        symbol_col = col
                        break

                if symbol_col:
                    row = df[df[symbol_col].str.upper() == symbol.upper()]
                    if not row.empty:
                        return row.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Error fetching price for {symbol} from list: {e}")

        return None

    def get_historical_prices(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get historical price data for a stock.

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            DataFrame with OHLCV data
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            from bdshare import get_hist_data
            df = get_hist_data(start_date, end_date, symbol)
            if df is not None and not df.empty:
                df.columns = df.columns.str.lower().str.replace(' ', '_')
                return df
        except Exception as e:
            logger.error(f"Error fetching historical data from bdshare: {e}")

        # Fallback to stocksurferbd
        try:
            from stocksurferbd import PriceData
            file_path = os.path.join(self.data_dir, f"{symbol}_history.xlsx")
            PriceData().save_history_data(symbol=symbol, file_name=file_path, market='DSE')
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data from stocksurferbd: {e}")

        return pd.DataFrame()

    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data for a stock.

        This includes financial statements, ratios, and year-wise data.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with company_data and financial_data
        """
        result = {
            "symbol": symbol,
            "company_data": {},
            "financial_data": [],
            "success": False,
        }

        try:
            from stocksurferbd import FundamentalData

            # Save fundamental data (creates two Excel files)
            FundamentalData().save_company_data(symbol, path=self.data_dir)

            # Read company data
            company_file = os.path.join(self.data_dir, f"{symbol}_company_data.xlsx")
            if os.path.exists(company_file):
                company_df = pd.read_excel(company_file)
                # stocksurferbd returns single row with many columns
                if not company_df.empty:
                    result["company_data"] = company_df.iloc[0].to_dict()

            # Read financial data (year-wise)
            financial_file = os.path.join(self.data_dir, f"{symbol}_financial_data.xlsx")
            if os.path.exists(financial_file):
                fin_df = pd.read_excel(financial_file)
                fin_df.columns = fin_df.columns.str.lower().str.replace(' ', '_').str.strip()

                # Convert to list of dicts (one per year)
                result["financial_data"] = fin_df.to_dict('records')

            result["success"] = True

        except Exception as e:
            logger.error(f"Error fetching fundamental data for {symbol}: {e}")
            result["error"] = str(e)

        return result

    def parse_financial_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse raw fundamental data into structured format for calculations.

        Args:
            raw_data: Output from get_fundamental_data()

        Returns:
            List of yearly financial records with standardized fields
        """
        parsed = []

        financial_data = raw_data.get("financial_data", [])

        for record in financial_data:
            # Try to extract year
            year = None
            for key in ['year', 'fiscal_year', 'period']:
                if key in record:
                    try:
                        year = int(record[key])
                    except (ValueError, TypeError):
                        # Try to extract year from string like "2023-2024"
                        val = str(record[key])
                        if '-' in val:
                            year = int(val.split('-')[0])
                        elif len(val) == 4:
                            year = int(val)

            if not year:
                continue

            # Map fields to our schema
            # stocksurferbd uses: eps_cop_original, nav_original, profit, pco, pe_cop_original
            parsed_record = {
                "year": year,
                "revenue": self._get_numeric(record, ['revenue', 'total_revenue', 'turnover', 'sales', 'pco']),
                "gross_profit": self._get_numeric(record, ['gross_profit', 'gross_income']),
                "operating_income": self._get_numeric(record, ['operating_income', 'operating_profit', 'ebit', 'pco']),
                "net_income": self._get_numeric(record, ['net_income', 'net_profit', 'profit_after_tax', 'pat', 'profit', 'tci']),
                "eps": self._get_numeric(record, ['eps', 'eps_cop_original', 'eps_original', 'eps_restated', 'earnings_per_share']),
                "total_assets": self._get_numeric(record, ['total_assets', 'assets']),
                "total_liabilities": self._get_numeric(record, ['total_liabilities', 'liabilities']),
                "total_equity": self._get_numeric(record, ['total_equity', 'equity', 'shareholders_equity', 'book_value', 'nav_original', 'nav_restated']),
                "total_debt": self._get_numeric(record, ['total_debt', 'debt', 'long_term_debt']),
                "operating_cash_flow": self._get_numeric(record, ['operating_cash_flow', 'ocf', 'cash_from_operations']),
                "capital_expenditure": self._get_numeric(record, ['capital_expenditure', 'capex', 'ppe_purchases']),
                "roe": self._get_numeric(record, ['roe', 'return_on_equity']),
                "roa": self._get_numeric(record, ['roa', 'return_on_assets']),
                "pe_ratio": self._get_numeric(record, ['pe_ratio', 'pe', 'p/e', 'pe_cop_original', 'pe_original']),
                "gross_margin": self._get_numeric(record, ['gross_margin', 'gross_margin_%']),
                "debt_to_equity": self._get_numeric(record, ['debt_to_equity', 'd/e', 'de_ratio']),
            }

            # Calculate free cash flow if not present
            if parsed_record["operating_cash_flow"] and parsed_record["capital_expenditure"]:
                parsed_record["free_cash_flow"] = (
                    parsed_record["operating_cash_flow"] -
                    abs(parsed_record["capital_expenditure"])
                )
            else:
                parsed_record["free_cash_flow"] = self._get_numeric(record, ['free_cash_flow', 'fcf'])

            parsed.append(parsed_record)

        # Sort by year (oldest first)
        parsed.sort(key=lambda x: x["year"])

        return parsed

    def _get_numeric(self, record: Dict, keys: List[str]) -> Optional[float]:
        """Extract numeric value from record using multiple possible keys.

        Args:
            record: Data record dict
            keys: List of possible key names to try

        Returns:
            Numeric value or None
        """
        for key in keys:
            # Try exact match
            if key in record:
                val = record[key]
                if val is not None and val != '' and not pd.isna(val):
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        continue

            # Try case-insensitive match
            for rec_key in record.keys():
                if rec_key.lower().replace(' ', '_') == key.lower():
                    val = record[rec_key]
                    if val is not None and val != '' and not pd.isna(val):
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            continue

        return None

    def get_market_depth(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order book / market depth for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with buy/sell orders or None
        """
        try:
            from bdshare import get_market_depth_data
            df = get_market_depth_data(symbol)
            if df is not None and not df.empty:
                df.columns = df.columns.str.lower().str.replace(' ', '_')
                return {
                    "symbol": symbol,
                    "orders": df.to_dict('records')
                }
        except Exception as e:
            logger.error(f"Error fetching market depth for {symbol}: {e}")

        return None

    def get_news(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get market news and announcements.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with news items
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            from bdshare import get_all_news
            df = get_all_news(start_date, end_date)
            if df is not None and not df.empty:
                df.columns = df.columns.str.lower().str.replace(' ', '_')
                return df
        except Exception as e:
            logger.error(f"Error fetching news: {e}")

        return pd.DataFrame()
