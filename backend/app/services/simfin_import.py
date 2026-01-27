"""
SimFin Data Import Service

Downloads bulk financial data from SimFin and imports into our database.
Replaces Finnhub data with cleaner, standardized SimFin data.

Usage:
    python -m app.services.simfin_import

API Key: Set SIMFIN_API_KEY environment variable or pass directly.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

import simfin as sf
from simfin.names import *
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SimFin API Configuration
SIMFIN_API_KEY = os.getenv("SIMFIN_API_KEY", "83a17c9a-cd93-47c8-b47e-bec3e4cd23c2")
SIMFIN_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../../simfin_data")


def setup_simfin():
    """Initialize SimFin with API key and data directory."""
    sf.set_api_key(SIMFIN_API_KEY)
    sf.set_data_dir(SIMFIN_DATA_DIR)
    os.makedirs(SIMFIN_DATA_DIR, exist_ok=True)
    logger.info(f"SimFin configured. Data dir: {SIMFIN_DATA_DIR}")


def download_all_datasets() -> Dict[str, pd.DataFrame]:
    """
    Download all required datasets from SimFin.

    Returns dict with keys: 'income', 'balance', 'cashflow', 'derived', 'companies'
    """
    logger.info("Downloading SimFin datasets...")

    datasets = {}

    # Download Income Statement (Annual, USA)
    logger.info("Downloading Income Statement...")
    datasets['income'] = sf.load_income(
        variant='annual',
        market='us',
        refresh_days=0  # Force fresh download
    )
    logger.info(f"  Income Statement: {len(datasets['income'])} rows")

    # Download Balance Sheet (Annual, USA)
    logger.info("Downloading Balance Sheet...")
    datasets['balance'] = sf.load_balance(
        variant='annual',
        market='us',
        refresh_days=0
    )
    logger.info(f"  Balance Sheet: {len(datasets['balance'])} rows")

    # Download Cash Flow (Annual, USA)
    logger.info("Downloading Cash Flow...")
    datasets['cashflow'] = sf.load_cashflow(
        variant='annual',
        market='us',
        refresh_days=0
    )
    logger.info(f"  Cash Flow: {len(datasets['cashflow'])} rows")

    # Download Derived Figures & Ratios (Annual, USA)
    logger.info("Downloading Derived Ratios...")
    try:
        datasets['derived'] = sf.load_derived(
            variant='annual',
            market='us',
            refresh_days=0
        )
        logger.info(f"  Derived Ratios: {len(datasets['derived'])} rows")
    except Exception as e:
        logger.warning(f"  Could not load derived ratios: {e}")
        datasets['derived'] = None

    # Download Companies list
    logger.info("Downloading Companies...")
    datasets['companies'] = sf.load_companies(market='us')
    logger.info(f"  Companies: {len(datasets['companies'])} rows")

    return datasets


def get_fiscal_year(report_date) -> int:
    """Extract fiscal year from report date."""
    if pd.isna(report_date):
        return None
    if isinstance(report_date, str):
        return int(report_date[:4])
    return report_date.year


def merge_financial_data(datasets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge income, balance, cashflow, and derived data into a single DataFrame.

    Returns DataFrame with columns matching our database schema.
    """
    logger.info("Merging financial datasets...")

    income = datasets['income'].reset_index()
    balance = datasets['balance'].reset_index()
    cashflow = datasets['cashflow'].reset_index()

    # Rename columns for clarity before merge
    income = income.rename(columns={'Ticker': 'symbol'})
    balance = balance.rename(columns={'Ticker': 'symbol'})
    cashflow = cashflow.rename(columns={'Ticker': 'symbol'})

    # Extract fiscal year from Report Date
    income['year'] = income['Fiscal Year'].astype(int)
    balance['year'] = balance['Fiscal Year'].astype(int)
    cashflow['year'] = cashflow['Fiscal Year'].astype(int)

    # Select and rename columns from Income Statement
    income_cols = income[['symbol', 'year']].copy()

    # Map SimFin columns to our schema
    if 'Revenue' in income.columns:
        income_cols['revenue'] = income['Revenue']
    if 'Gross Profit' in income.columns:
        income_cols['gross_profit'] = income['Gross Profit']
    if 'Operating Income (Loss)' in income.columns:
        income_cols['operating_income'] = income['Operating Income (Loss)']
    if 'Net Income' in income.columns:
        income_cols['net_income'] = income['Net Income']

    # EPS - prefer diluted
    if 'Earnings Per Share, Diluted' in income.columns:
        income_cols['eps'] = income['Earnings Per Share, Diluted']
    elif 'Earnings Per Share, Basic' in income.columns:
        income_cols['eps'] = income['Earnings Per Share, Basic']

    # Select columns from Balance Sheet
    balance_cols = balance[['symbol', 'year']].copy()

    if 'Total Assets' in balance.columns:
        balance_cols['total_assets'] = balance['Total Assets']
    if 'Total Liabilities' in balance.columns:
        balance_cols['total_liabilities'] = balance['Total Liabilities']
    if 'Total Current Liabilities' in balance.columns:
        balance_cols['current_liabilities'] = balance['Total Current Liabilities']
    if 'Total Equity' in balance.columns:
        balance_cols['total_equity'] = balance['Total Equity']

    # Total Debt - try multiple column names
    debt_columns = ['Total Debt', 'Long Term Debt', 'Short Long Term Debt']
    for col in debt_columns:
        if col in balance.columns:
            balance_cols['total_debt'] = balance[col]
            break

    # Select columns from Cash Flow
    cashflow_cols = cashflow[['symbol', 'year']].copy()

    # Operating Cash Flow - try multiple names
    ocf_columns = ['Net Cash from Operating Activities', 'Cash from Operating Activities']
    for col in ocf_columns:
        if col in cashflow.columns:
            cashflow_cols['operating_cash_flow'] = cashflow[col]
            break

    # Capital Expenditure
    capex_columns = ['Capital Expenditures', 'Change in Fixed Assets & Intangibles']
    for col in capex_columns:
        if col in cashflow.columns:
            cashflow_cols['capital_expenditure'] = abs(cashflow[col])  # Make positive
            break

    # Free Cash Flow
    if 'Free Cash Flow' in cashflow.columns:
        cashflow_cols['free_cash_flow'] = cashflow['Free Cash Flow']

    # Merge all dataframes
    merged = income_cols.merge(
        balance_cols,
        on=['symbol', 'year'],
        how='outer'
    ).merge(
        cashflow_cols,
        on=['symbol', 'year'],
        how='outer'
    )

    # Add derived ratios if available
    if datasets['derived'] is not None:
        derived = datasets['derived'].reset_index()
        derived = derived.rename(columns={'Ticker': 'symbol'})
        derived['year'] = derived['Fiscal Year'].astype(int)

        derived_cols = derived[['symbol', 'year']].copy()

        if 'Return on Equity' in derived.columns:
            derived_cols['roe'] = derived['Return on Equity'] * 100  # Convert to percentage
        if 'Return on Assets' in derived.columns:
            derived_cols['roa'] = derived['Return on Assets'] * 100
        if 'Return on Invested Capital' in derived.columns:
            derived_cols['roic'] = derived['Return on Invested Capital'] * 100

        merged = merged.merge(derived_cols, on=['symbol', 'year'], how='left')

    # Calculate ratios if not from derived dataset
    if 'roe' not in merged.columns or merged['roe'].isna().all():
        merged['roe'] = merged.apply(
            lambda r: (r['net_income'] / r['total_equity'] * 100)
            if pd.notna(r.get('net_income')) and pd.notna(r.get('total_equity')) and r.get('total_equity', 0) > 0
            else None,
            axis=1
        )

    if 'debt_to_equity' not in merged.columns:
        merged['debt_to_equity'] = merged.apply(
            lambda r: (r['total_debt'] / r['total_equity'])
            if pd.notna(r.get('total_debt')) and pd.notna(r.get('total_equity')) and r.get('total_equity', 0) > 0
            else None,
            axis=1
        )

    # Calculate margins
    merged['gross_margin'] = merged.apply(
        lambda r: (r['gross_profit'] / r['revenue'] * 100)
        if pd.notna(r.get('gross_profit')) and pd.notna(r.get('revenue')) and r.get('revenue', 0) > 0
        else None,
        axis=1
    )

    merged['operating_margin'] = merged.apply(
        lambda r: (r['operating_income'] / r['revenue'] * 100)
        if pd.notna(r.get('operating_income')) and pd.notna(r.get('revenue')) and r.get('revenue', 0) > 0
        else None,
        axis=1
    )

    merged['net_margin'] = merged.apply(
        lambda r: (r['net_income'] / r['revenue'] * 100)
        if pd.notna(r.get('net_income')) and pd.notna(r.get('revenue')) and r.get('revenue', 0) > 0
        else None,
        axis=1
    )

    # Calculate Free Cash Flow if missing
    if 'free_cash_flow' not in merged.columns or merged['free_cash_flow'].isna().all():
        merged['free_cash_flow'] = merged.apply(
            lambda r: (r.get('operating_cash_flow', 0) or 0) - (r.get('capital_expenditure', 0) or 0)
            if pd.notna(r.get('operating_cash_flow'))
            else None,
            axis=1
        )

    # Add source column
    merged['source'] = 'simfin'

    # Filter out rows with no useful data
    # Only check columns that actually exist in the merged dataframe
    possible_required = ['revenue', 'net_income', 'eps', 'total_equity']
    required_cols = [col for col in possible_required if col in merged.columns]

    merged = merged.dropna(subset=['symbol', 'year'])
    if required_cols:
        merged = merged[merged[required_cols].notna().any(axis=1)]

    logger.info(f"Merged dataset: {len(merged)} rows, {merged['symbol'].nunique()} unique stocks")

    return merged


def prepare_for_database(df: pd.DataFrame) -> List[Dict]:
    """
    Convert DataFrame to list of dicts ready for database insertion.
    Handles NaN values and type conversions.
    """
    records = []

    for _, row in df.iterrows():
        record = {
            'stock_symbol': row['symbol'],
            'year': int(row['year']),
            'source': 'simfin'
        }

        # Integer fields (BigInteger in DB)
        int_fields = [
            'revenue', 'gross_profit', 'operating_income', 'net_income',
            'total_assets', 'total_liabilities', 'current_liabilities',
            'total_equity', 'total_debt',
            'operating_cash_flow', 'capital_expenditure', 'free_cash_flow'
        ]

        for field in int_fields:
            if field in row and pd.notna(row[field]):
                record[field] = int(row[field])
            else:
                record[field] = None

        # Float fields
        float_fields = [
            'eps', 'roe', 'roic', 'roa', 'debt_to_equity',
            'gross_margin', 'operating_margin', 'net_margin'
        ]

        for field in float_fields:
            if field in row and pd.notna(row[field]):
                record[field] = round(float(row[field]), 4)
            else:
                record[field] = None

        records.append(record)

    return records


def import_to_database(records: List[Dict], batch_size: int = 1000):
    """
    Import records to Supabase database.
    Uses upsert to update existing records or insert new ones.
    """
    from app.database import SessionLocal
    from app.models.us_stock import USFinancialData
    from sqlalchemy import text

    db = SessionLocal()

    try:
        total = len(records)
        imported = 0
        updated = 0

        logger.info(f"Importing {total} records to database...")

        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]

            for record in batch:
                # Check if record exists
                existing = db.query(USFinancialData).filter(
                    USFinancialData.stock_symbol == record['stock_symbol'],
                    USFinancialData.year == record['year']
                ).first()

                if existing:
                    # Update existing record
                    for key, value in record.items():
                        if key not in ['stock_symbol', 'year'] and value is not None:
                            setattr(existing, key, value)
                    existing.source = 'simfin'
                    updated += 1
                else:
                    # Insert new record
                    new_record = USFinancialData(**record)
                    db.add(new_record)
                    imported += 1

            db.commit()
            logger.info(f"  Progress: {min(i + batch_size, total)}/{total} ({imported} new, {updated} updated)")

        logger.info(f"Import complete: {imported} new records, {updated} updated records")
        return imported, updated

    except Exception as e:
        db.rollback()
        logger.error(f"Database import failed: {e}")
        raise
    finally:
        db.close()


def generate_sql_file(records: List[Dict], output_file: str = "simfin_import.sql"):
    """
    Generate SQL file for manual import (alternative to direct DB connection).
    """
    logger.info(f"Generating SQL file: {output_file}")

    with open(output_file, 'w') as f:
        f.write("-- SimFin Data Import\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Total records: {len(records)}\n\n")

        for record in records:
            cols = []
            vals = []

            for key, value in record.items():
                cols.append(key)
                if value is None:
                    vals.append("NULL")
                elif isinstance(value, str):
                    vals.append(f"'{value}'")
                else:
                    vals.append(str(value))

            f.write(f"INSERT INTO us_financial_data ({', '.join(cols)}) VALUES ({', '.join(vals)}) ")
            f.write(f"ON CONFLICT (stock_symbol, year) DO UPDATE SET ")

            updates = []
            for key in record.keys():
                if key not in ['stock_symbol', 'year']:
                    updates.append(f"{key} = EXCLUDED.{key}")
            f.write(", ".join(updates))
            f.write(";\n")

    logger.info(f"SQL file generated: {output_file}")


def run_full_import(to_database: bool = True, generate_sql: bool = False):
    """
    Run the full import process.

    Args:
        to_database: If True, import directly to database
        generate_sql: If True, generate SQL file for manual import
    """
    logger.info("=" * 60)
    logger.info("SimFin Data Import - Starting")
    logger.info("=" * 60)

    # Setup
    setup_simfin()

    # Download datasets
    datasets = download_all_datasets()

    # Merge data
    merged_df = merge_financial_data(datasets)

    # Prepare records
    records = prepare_for_database(merged_df)
    logger.info(f"Prepared {len(records)} records for import")

    # Save merged data to CSV for reference
    csv_file = os.path.join(SIMFIN_DATA_DIR, "merged_financial_data.csv")
    merged_df.to_csv(csv_file, index=False)
    logger.info(f"Saved merged data to: {csv_file}")

    # Import to database
    if to_database:
        imported, updated = import_to_database(records)

    # Generate SQL file
    if generate_sql:
        sql_file = os.path.join(SIMFIN_DATA_DIR, "simfin_import.sql")
        generate_sql_file(records, sql_file)

    logger.info("=" * 60)
    logger.info("SimFin Data Import - Complete")
    logger.info("=" * 60)

    return records


if __name__ == "__main__":
    # Run import
    run_full_import(to_database=True, generate_sql=True)
