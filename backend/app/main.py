"""DSE Value Investor - FastAPI Application.

A comprehensive stock analysis application for the Dhaka Stock Exchange
based on Phil Town's Rule #1 Investing methodology.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import init_db
from app.routers import portfolio, stocks, calculator
from app.routers import us_stocks
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

    # Start scheduler for live price updates (every 30 min during US market hours)
    # Fundamentals come from SimFin bulk import, scheduler only handles prices
    if settings.us_stocks_enabled and settings.finnhub_api_key:
        from app.scheduler import start_scheduler
        start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if settings.us_stocks_enabled:
        from app.scheduler import stop_scheduler
        stop_scheduler()


# Include routers
app.include_router(portfolio.router)
app.include_router(stocks.router)
app.include_router(calculator.router)
app.include_router(us_stocks.router)


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


@app.get("/scheduler-status", tags=["Health"])
def scheduler_status():
    """Check scheduler status."""
    from app.scheduler import scheduler
    jobs = scheduler.get_jobs()
    return {
        "scheduler_running": scheduler.running,
        "job_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
            for job in jobs
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
