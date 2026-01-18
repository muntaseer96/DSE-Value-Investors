# STOKR - Codebase Guide for Claude

## Quick Reference

| Component | Technology | Deployment | URL/ID |
|-----------|------------|------------|--------|
| **Frontend** | SvelteKit + TypeScript | **Netlify** | `dsevalueinvestors.netlify.app` |
| **Backend** | FastAPI + Python | **Railway** | Auto-deploys on push |
| **Database** | PostgreSQL | **Supabase** | Project ID: `kjjringoshpczqttxaib` |

## Project Overview

**Stokr** (rebranded from DSE Value Investor) is a stock analysis app for the **Dhaka Stock Exchange (DSE)** based on **Phil Town's Rule #1 Investing** methodology.

**Features:**
- Portfolio tracking with live P&L
- Stock browser with search/filter/sort
- Rule #1 Calculator (Sticker Price, Big Five, 4Ms)
- Financial data scraping from LankaBD

---

## Directory Structure

```
Stock Investment/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── main.py            # App entry point
│   │   ├── config.py          # Environment config
│   │   ├── database.py        # SQLAlchemy setup
│   │   ├── models/            # Stock, Portfolio, FinancialData
│   │   ├── routers/           # API endpoints
│   │   │   ├── stocks.py      # Stock data + scraping
│   │   │   ├── portfolio.py   # Portfolio CRUD
│   │   │   └── calculator.py  # Valuations
│   │   ├── services/
│   │   │   ├── dse_data.py    # External data fetching
│   │   │   └── lankabd_scraper.py  # Playwright scraper
│   │   └── calculations/
│   │       ├── sticker_price.py
│   │       ├── big_five.py
│   │       └── four_ms.py
│   ├── requirements.txt
│   └── run.py
│
├── frontend/                   # SvelteKit frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/client.ts  # API client + types
│   │   │   └── stores/        # Svelte stores
│   │   └── routes/
│   │       ├── +page.svelte           # Portfolio
│   │       ├── stocks/+page.svelte    # Stock browser
│   │       ├── calculator/+page.svelte # Calculator
│   │       └── admin/+page.svelte     # Data entry
│   └── package.json
│
└── CLAUDE.md                   # This file
```

---

## Deployment

### Frontend (Netlify)
- **Auto-deploys** when `frontend/` files change
- Build: `npm run build`
- Publish: `frontend/build`
- Env: `VITE_API_URL` = Railway backend URL

### Backend (Railway)
- **Auto-deploys** when `backend/` files change on push to main
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env: `DATABASE_URL` = Supabase connection string

### Database (Supabase)
- **Project ID**: `kjjringoshpczqttxaib`
- PostgreSQL with connection pooling (port 6543)
- Tables: `stocks`, `financial_data`, `portfolio_holdings`, `price_history`

---

## Key API Endpoints

```
GET  /stocks/prices              # All DSE stock prices
GET  /stocks/{symbol}            # Single stock price
GET  /stocks/{symbol}/fundamentals  # Financial data

POST /calculate/sticker-price    # Manual calculation
GET  /calculate/sticker-price/{symbol}  # Auto calculation
GET  /calculate/big-five/{symbol}       # Big Five Numbers
GET  /calculate/analysis/{symbol}       # Full Rule #1 analysis

GET  /portfolio/                 # All holdings with P&L
POST /portfolio/                 # Add holding
```

---

## Calculations (Phil Town's Rule #1)

### Sticker Price
- Project EPS 10 years at capped growth (max 15%)
- Apply PE ratio (Growth% × 2, capped by historical)
- Discount back at 15% required return
- Margin of Safety = Sticker × 50%

### Big Five Numbers
5 metrics need ≥10% CAGR (need 3/5 to pass):
1. Revenue Growth
2. EPS Growth
3. Book Value Growth
4. Operating Cash Flow Growth
5. Free Cash Flow Growth

**Special Statuses** (for problematic data):
- `NEGATIVE` - 70%+ years negative (cash burning)
- `INCONSISTENT` - 30-70% years negative
- `NO_DATA` - Insufficient data

### Four Ms
1. **Meaning** - Do I understand the business?
2. **Moat** - Competitive advantage (ROE, margins)
3. **Management** - Owner-oriented (D/E, insider ownership)
4. **Margin of Safety** - Price vs Sticker

---

## LankaBD Scraper

**Purpose**: Scrape financial statements (Balance Sheet, Income Statement, Cash Flow) from lankabd.com

**Location**: `backend/app/services/lankabd_scraper.py`

**Key Features**:
- Playwright headless browser
- 100+ field name variations mapped
- Handles typos: "Acquision", "Aquisition"
- Rate limited (2s delay)
- Async batch processing

**Usage**:
```python
async with LankaBDScraper() as scraper:
    result = await scraper.scrape_stock('BXPHARMA')
```

---

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://...  # Supabase connection
FRONTEND_URL=https://dsevalueinvestors.netlify.app
DEBUG=False
```

### Frontend (.env)
```
VITE_API_URL=https://your-railway-app.railway.app
```

---

## Common Tasks

### Add new stock to scraper
Edit `backend/rescrape_all_years.py` → `ALL_STOCKS` list

### Update CapEx field mappings
Edit `backend/app/services/lankabd_scraper.py` → `FIELD_MAPPINGS`

### Run local development
```bash
# Backend
cd backend && python run.py

# Frontend
cd frontend && npm run dev
```

### Execute SQL on Supabase
Use MCP tool: `mcp__plugin_supabase_supabase__execute_sql`
Project ID: `kjjringoshpczqttxaib`

---

## User's Portfolio (Demo Data)
- BXPHARMA: 779 shares @ ৳135.02
- SQURPHARMA: 1215 shares @ ৳212.17
- MARICO: 14 shares @ ৳2332.02
- OLYMPIC: 397 shares @ ৳125.69

---

## Recent Changes Log

### 2026-01-18
- Added NEGATIVE/INCONSISTENT/NO_DATA statuses to Big Five calculator
- Fixed frontend crash when cagr_pct is null
- Added "Aquisition" typo variant to scraper
- Updated BEACHHATCH with 2022 CapEx data

---

## Notes

- Financial institutions (banks, NBFIs) don't have CapEx - this is expected
- Some companies have incomplete Cash Flow data on LankaBD
- CAGR calculation filters out negative values (can't compound negatives)
- Always push both backend AND frontend changes if they're related
