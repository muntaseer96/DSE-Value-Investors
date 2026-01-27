# STOKR - Codebase Guide for Claude

## Quick Reference

| Component | Technology | Deployment | URL |
|-----------|------------|------------|-----|
| **Frontend** | SvelteKit + TypeScript | Netlify | `https://dsevalueinvestors.netlify.app` |
| **Backend** | FastAPI + Python | Railway | `https://dse-value-investors-production.up.railway.app` |
| **Database** | PostgreSQL | Supabase | Project ID: `kjjringoshpczqttxaib` |

**Railway Project**: `https://railway.com/project/68351fb6-0dbd-42d5-9049-3d803e7bfc74`

---

## Project Overview

**Stokr** is a stock analysis app based on **Phil Town's Rule #1 Investing** methodology. Supports both:
- **Dhaka Stock Exchange (DSE)** - Bangladesh stocks
- **US Stocks** - NYSE/NASDAQ with S&P 500 tracking

**Features:**
- Portfolio tracking with live P&L (DSE)
- Stock browser with search/filter/sort (DSE + US)
- Rule #1 Calculator (Sticker Price, Big Five, 4Ms)
- Automated financial data scraping
- Phil Score ranking system

---

## Data Sources

### DSE Stocks
| Data Type | Source | Notes |
|-----------|--------|-------|
| **Live Prices** | `bdshare` Python library | Returns LTP=0 when market closed (10am-2:30pm Sun-Thu Bangladesh time). Backend falls back to YCP (yesterday's close) when LTP=0 |
| **Fundamentals** | LankaBD scraper (`lankabd_scraper.py`) | Playwright headless browser, scrapes Balance Sheet/Income Statement/Cash Flow |

### US Stocks
| Data Type | Source | Notes |
|-----------|--------|-------|
| **Quotes** | Finnhub API | Primary source. Falls back to `yfinance` if Finnhub returns no data |
| **Fundamentals** | Finnhub API | SEC-reported financials (10-K filings) |
| **Stock Splits** | `yfinance` | Auto-detects and adjusts EPS for splits (2014+ only, older already in SEC data) |

**API Keys Required:**
- `FINNHUB_API_KEY` - For US stock data (60 calls/min rate limit)

---

## Directory Structure

```
Stock Investment/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings & env vars
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models/
│   │   │   ├── stock.py            # DSE Stock model
│   │   │   └── us_stock.py         # US Stock model
│   │   ├── routers/
│   │   │   ├── stocks.py           # DSE stock endpoints
│   │   │   ├── us_stocks.py        # US stock endpoints
│   │   │   ├── portfolio.py        # Portfolio CRUD
│   │   │   └── calculator.py       # Valuation calculations
│   │   ├── services/
│   │   │   ├── dse_data.py         # bdshare wrapper
│   │   │   ├── lankabd_scraper.py  # DSE fundamentals scraper
│   │   │   └── finnhub_service.py  # US stocks API + yfinance fallback
│   │   └── calculations/
│   │       ├── sticker_price.py
│   │       ├── big_five.py
│   │       └── four_ms.py
│   ├── stock_data/                 # Stock split configs
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/client.ts       # API client & types
│   │   │   └── stores/             # Svelte stores
│   │   └── routes/
│   │       ├── +page.svelte              # Portfolio (DSE)
│   │       ├── stocks/+page.svelte       # DSE stock browser
│   │       ├── us-stocks/+page.svelte    # US stock browser
│   │       ├── us-stocks/[symbol]/       # US stock analysis
│   │       ├── calculator/+page.svelte   # Manual calculator
│   │       └── admin/+page.svelte        # Data scraping admin
│   └── package.json
│
└── CLAUDE.md
```

---

## Database Tables (Supabase)

### DSE Stocks
- `stocks` - DSE stock prices & metadata
- `financial_data` - DSE company financials by year
- `portfolio_holdings` - User portfolio
- `price_history` - Historical DSE prices

### US Stocks
- `us_stocks` - US stock prices, valuations, recommendations
- `us_financial_data` - US company financials by year (from SEC filings)

---

## Key API Endpoints

### DSE Stocks
```
GET  /stocks/prices                    # All DSE prices (uses YCP if LTP=0)
GET  /stocks/{symbol}                  # Single stock price
GET  /stocks/{symbol}/fundamentals     # Financial data
GET  /calculate/analysis/{symbol}      # Full Rule #1 analysis
```

### US Stocks
```
GET  /us-stocks/prices                 # All US stocks with valuations
GET  /us-stocks/{symbol}               # Single stock details
GET  /us-stocks/{symbol}/fundamentals  # Financial history
GET  /us-stocks/{symbol}/analysis      # Full Rule #1 analysis
GET  /us-stocks/filter-counts          # Counts for filters
POST /us-stocks/seed                   # Seed stock symbols from Finnhub
POST /us-stocks/trigger-scrape         # Scrape fundamentals batch
POST /us-stocks/trigger-scrape?symbol=AAPL  # Scrape single stock
GET  /us-stocks/scrape-status          # Check scrape progress
```

### Portfolio
```
GET  /portfolio/                       # All holdings with P&L
POST /portfolio/                       # Add holding
```

---

## Calculations (Phil Town's Rule #1)

### Sticker Price
- Project EPS 10 years at capped growth (max 15%)
- Apply PE ratio (Growth% × 2, capped by historical)
- Discount back at 15% required return
- **Margin of Safety = Sticker × 50%**

### Big Five Numbers
5 metrics need ≥10% CAGR (need 3/5 to pass):
1. Revenue Growth
2. EPS Growth
3. Book Value (Equity) Growth
4. Operating Cash Flow Growth
5. Free Cash Flow Growth

**Special Statuses:**
- `NEGATIVE` - 70%+ years negative
- `INCONSISTENT` - 30-70% years negative
- `NO_DATA` - Insufficient data

### Four Ms → Phil Score
1. **Meaning** - Business understandability
2. **Moat** - Competitive advantage (ROE, margins)
3. **Management** - Owner-oriented (D/E ratio)
4. **Margin of Safety** - Price vs Sticker

**Grades:** A (80+), B (60-79), C (40-59), D (20-39), F (<20)

---

## Environment Variables

### Backend (Railway)
```
DATABASE_URL=postgresql://...         # Supabase connection string
FINNHUB_API_KEY=...                   # For US stock data
FRONTEND_URL=https://dsevalueinvestors.netlify.app
DEBUG=False
```

### Frontend (Netlify)
```
VITE_API_URL=https://dse-value-investors-production.up.railway.app
```

---

## Deployment

### Auto-Deploy Flow
1. Push to `main` branch
2. Railway auto-deploys backend (~2-3 min)
3. Netlify auto-deploys frontend (~1-2 min)

### Manual Commands
```bash
# Local backend
cd backend && python run.py

# Local frontend
cd frontend && npm run dev
```

### Supabase SQL
Use MCP tool: `mcp__plugin_supabase_supabase__execute_sql`
Project ID: `kjjringoshpczqttxaib`

---

## Common Issues & Fixes

### DSE Prices Show 0
- **Cause**: Market closed (10am-2:30pm Sun-Thu Bangladesh time)
- **Fix**: Backend uses YCP (yesterday's close) as fallback

### US Stock Missing Price
- **Cause**: Finnhub doesn't provide quotes for all stocks
- **Fix**: yfinance fallback added (2026-01-22)
- **Action**: Re-scrape the stock: `POST /us-stocks/trigger-scrape?symbol=XXX`

### LankaBD Scraper Field Not Found
- **Cause**: Website uses variant field names
- **Fix**: Add mapping to `FIELD_MAPPINGS` in `lankabd_scraper.py`

### Finnhub EPS Data Quality Issues (e.g., Visa)
- **Cause**: Some stocks (like V/Visa) have incorrect EPS in Finnhub's SEC data - often 6-8x too high due to wrong share count calculations
- **Symptoms**: Absurdly low sticker price, negative EPS growth despite growing company
- **Detection**: Compare DB EPS with yfinance: `python -c "import yfinance as yf; print(yf.Ticker('V').income_stmt.loc['Basic EPS'])"`
- **Fix implemented**:
  1. `FINNHUB_EPS_PROBLEM_SYMBOLS` set in `finnhub_service.py` - identifies affected stocks
  2. `_get_yfinance_eps()` function - fetches correct EPS from yfinance
  3. `HARDCODED_EPS_OVERRIDES` dict - fallback when yfinance fails (common on Railway due to Yahoo rate limiting)
  4. Scraper skips split adjustment for problem stocks (yfinance data already adjusted)
- **To add a new problem stock**:
  1. Add symbol to `FINNHUB_EPS_PROBLEM_SYMBOLS`
  2. Add correct EPS values to `HARDCODED_EPS_OVERRIDES` (get from yfinance locally)
  3. Re-scrape: `POST /us-stocks/trigger-scrape?symbol=XXX`
- **Currently affected**: V (Visa)

### yfinance Fails on Railway
- **Cause**: Yahoo Finance rate limits or blocks Railway's IP addresses
- **Symptoms**: Logs show `'Ticker' object has no attribute 'income_stmt'` or `Expecting value: line 1 column 1`
- **Fix**: Use `HARDCODED_EPS_OVERRIDES` as fallback - yfinance works locally but often fails in production

---

## Notes

- Financial institutions (banks, NBFIs) don't have CapEx - expected
- US stocks: Only "Common Stock" type scraped (skip ETFs, ADRs)
- Stock splits auto-adjust historical EPS via `stock_data/stock_splits.py`
- Finnhub rate limit: 60 calls/min (RateLimiter class handles this)
- Always push backend + frontend together if changes are related

---

## Recent Changes

### 2026-01-27 (Update 3)
- **Fixed Visa (V) EPS bug** - Finnhub returns ~8x inflated EPS for Visa due to wrong share count
  - Root cause: Finnhub's SEC parser uses incorrect share count for V (248M vs actual 1.7B)
  - Added `FINNHUB_EPS_PROBLEM_SYMBOLS` set to identify affected stocks
  - Added `_get_yfinance_eps()` function as primary fallback
  - Added `HARDCODED_EPS_OVERRIDES` dict as secondary fallback (yfinance fails on Railway)
  - Modified scraper to skip split adjustment for problem stocks
  - **Before**: EPS $79.62, Sticker $13.95, EPS Growth -0.08%
  - **After**: EPS $9.74, Sticker $150.59, EPS Growth 14.8%

### 2026-01-27 (Update 2)
- **Fixed ORLY valuation bugs** - Three critical fixes for US stock calculations:
  1. **Replaced hardcoded stock splits with yfinance API** in `stock_splits.py`
     - Now uses yfinance as source of truth for split detection
     - Automatically detects ALL stock splits (no manual dictionary updates needed)
     - Only considers splits from 2014+ (older splits already reflected in SEC data)
     - Keeps hardcoded `FALLBACK_SPLITS` dictionary as backup if yfinance fails
     - Cache prevents repeated API calls for same symbol
  2. **Fixed CAGR year calculation** in `big_five.py`
     - Now uses actual calendar years instead of array indices
     - Prevents inflated growth rates when negative years are filtered out
     - Example: 100→200 over 10 years now correctly shows 7.2% CAGR, not 18.9%
  3. **Handle negative equity in ROE** in `us_stocks.py` and `four_ms.py`
     - ROE set to None when equity is negative (aggressive buybacks)
     - Moat/Management scores use neutral values instead of misleading high ROE
     - Added explanatory notes: "ROE unavailable (negative equity from stock buybacks)"
- **Affected stocks**: ORLY, AZO, NVR, and any other high-buyback companies with negative equity
- **Action required**: Re-scrape affected stocks with `POST /us-stocks/trigger-scrape?symbol=ORLY`

### 2026-01-27
- **Disabled Railway scheduler** - Now using GitHub Actions only for US stock scraping
  - Railway's internal scheduler was running in parallel, wasting API calls on non-Common Stock types
  - GitHub Action (every 3 hours) properly filters for Common Stock via `/trigger-scrape` endpoint
- **Filtered US stocks to Common Stock only** in all API endpoints:
  - `/us-stocks/prices`, `/us-stocks/count`, `/us-stocks/filter-counts`, `/us-stocks/sectors`
  - Excludes ETFs, REITs, ADRs, and other non-operating securities from Phil Town valuations
  - Table now shows 18,320 stocks instead of 29,317
- **Removed "X attempted" indicator** from US stocks page (no longer needed since all Common Stocks scraped)
- **Investigated GitHub Actions schedule** - found 00:00 UTC runs can be delayed 1+ hours during high traffic
- **Scraper cycling confirmed working** - re-scrapes from oldest `last_fundamental_update` after completing all Common Stocks

### 2026-01-22
- Fixed DSE prices to show YCP when LTP=0 (market closed)
- Added yfinance fallback for US stock quotes when Finnhub fails
- US stocks Analyze button now opens in new tab
- Re-scraped 13 US stocks that were missing prices

### 2026-01-20
- Added server-side search for US stocks

### 2026-01-18
- Added NEGATIVE/INCONSISTENT/NO_DATA statuses to Big Five
- Fixed frontend crash when cagr_pct is null
- Added "Aquisition" typo variant to scraper
