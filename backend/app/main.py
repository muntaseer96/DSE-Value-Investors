"""DSE Value Investor - FastAPI Application.

A comprehensive stock analysis application for the Dhaka Stock Exchange
based on Phil Town's Rule #1 Investing methodology.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import init_db
from app.routers import portfolio, stocks, calculator
from app.config import get_settings

settings = get_settings()

# Create data directory (for SQLite and downloaded files)
os.makedirs("data", exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="DSE Value Investor API",
    description="""
    Stock analysis and portfolio tracking for the Dhaka Stock Exchange.
    Based on Phil Town's Rule #1 Investing methodology.

    ## Features
    - **Portfolio Tracking**: Track your holdings with live P&L
    - **Sticker Price Calculator**: Calculate intrinsic value using Phil Town's method
    - **Big Five Numbers**: Evaluate growth rates (Revenue, EPS, Equity, OCF, FCF)
    - **4Ms Analysis**: Evaluate Meaning, Moat, Management, and Margin of Safety
    - **Stock Scanner**: Find undervalued stocks

    ## Data Sources
    - Real-time prices from bdshare
    - Fundamental data from stocksurferbd
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    settings.frontend_url,  # Production frontend URL
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    init_db()


# Include routers
app.include_router(portfolio.router)
app.include_router(stocks.router)
app.include_router(calculator.router)


# Health check endpoint
@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": "DSE Value Investor",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "sqlite",
        "data_sources": ["bdshare", "stocksurferbd"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
