# DSE Value Investor

A comprehensive stock analysis and portfolio tracking application for the **Dhaka Stock Exchange (DSE)**, built on **Phil Town's Rule #1 Investing** methodology.

## Features

- **Portfolio Tracker**: Track your holdings with live P&L calculations
- **Sticker Price Calculator**: Calculate intrinsic value using Phil Town's method
- **Big Five Numbers**: Evaluate growth rates (Revenue, EPS, Equity, OCF, FCF)
- **4Ms Analysis**: Evaluate Meaning, Moat, Management, and Margin of Safety
- **Stock Scanner**: Browse DSE stocks with live prices
- **Buy/Hold/Sell Recommendations**: Based on Sticker Price vs Current Price

---

## 🚀 Deploy to Render (Production)

### One-Click Deploy

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repo
5. Render will automatically create:
   - Backend API (Python)
   - Frontend (Static Site)
   - PostgreSQL Database

That's it! Your app will be live in ~5 minutes.

### Manual Deploy

See [Render Deployment Guide](#render-deployment-guide) below.

---

## 💻 Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+

### Quick Start (First Time)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### After Setup (Daily Use)

```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate && python run.py

# Terminal 2 - Frontend
cd frontend && npm run dev
```

**Open:** http://localhost:5173

---

## Project Structure

```
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── main.py         # API entry point
│   │   ├── config.py       # Environment configuration
│   │   ├── database.py     # PostgreSQL/SQLite setup
│   │   ├── models/         # Database models
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Data fetching
│   │   └── calculations/   # Phil Town logic
│   └── requirements.txt
├── frontend/                # SvelteKit frontend
│   ├── src/
│   │   ├── lib/api/        # API client
│   │   └── routes/         # Pages
│   └── package.json
├── render.yaml              # Render Blueprint (one-click deploy)
└── README.md
```

---

## API Endpoints

### Portfolio
- `GET /portfolio/` - Get portfolio with live P&L
- `POST /portfolio/` - Add a holding
- `POST /portfolio/seed` - Load preset stocks

### Stocks
- `GET /stocks/prices` - All DSE stock prices
- `GET /stocks/{symbol}` - Single stock price
- `GET /stocks/{symbol}/fundamentals` - Financial data

### Calculator
- `GET /calculate/analysis/{symbol}` - Full Rule #1 analysis
- `GET /calculate/sticker-price/{symbol}` - Sticker Price
- `GET /calculate/big-five/{symbol}` - Big Five Numbers

---

## Phil Town's Rule #1 Methodology

### Sticker Price Formula
1. Get 5-year EPS growth rate (CAGR)
2. Cap growth at 15% (conservative)
3. Project EPS 10 years forward
4. Apply PE ratio (Growth × 2)
5. Discount to present (15% annual return)
6. **Margin of Safety = 50% of Sticker**

### Big Five Numbers (need 3/5)
| Metric | Requirement |
|--------|-------------|
| Revenue Growth | >10% CAGR |
| EPS Growth | >10% CAGR |
| Book Value Growth | >10% CAGR |
| Operating CF Growth | >10% CAGR |
| Free CF Growth | >10% CAGR |

### Buy Signals
- **STRONG_BUY**: Price < Margin of Safety
- **BUY**: MOS < Price < Sticker
- **HOLD**: Price ≈ Sticker
- **SELL**: Price > Sticker × 1.25

---

## Your Portfolio

| Stock | DSE Symbol | Shares | Avg Cost |
|-------|------------|--------|----------|
| Beximco Pharma | BXPHARMA | 779 | ৳135.02 |
| Square Pharma | SQURPHARMA | 1,215 | ৳212.17 |
| Marico Bangladesh | MARICO | 14 | ৳2,332.02 |
| Olympic Industries | OLYMPIC | 397 | ৳125.69 |

---

## Render Deployment Guide

### Environment Variables

**Backend (dse-investor-api):**
```
DATABASE_URL=<from Render PostgreSQL>
FRONTEND_URL=https://your-frontend.onrender.com
```

**Frontend (dse-investor-frontend):**
```
VITE_API_URL=https://your-api.onrender.com
```

### Free Tier Limits
- Backend: Sleeps after 15 min inactivity (cold start ~30s)
- Database: 1GB storage, 90 days retention
- Upgrade to paid ($7/mo) for always-on

---

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: SvelteKit, TypeScript
- **Data**: stocksurferbd, bdshare (DSE APIs)
- **Deployment**: Render

## License

MIT
