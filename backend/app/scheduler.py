"""APScheduler setup for automated background tasks.

Note: Fundamental data now comes from SimFin bulk import.
Scheduler handles live price updates for ALL stocks in rotating batches.

Uses BackgroundScheduler (runs in thread pool) to avoid conflicts with
Uvicorn's event loop. The async FinnhubService calls are wrapped in
asyncio.run() since we're in a separate thread.
"""
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance - BackgroundScheduler runs in thread pool
scheduler = BackgroundScheduler()

# Batch size for price updates (respects Finnhub 60 calls/min rate limit)
# With 0.1s delay between calls, 500 stocks takes ~50 seconds
PRICE_UPDATE_BATCH_SIZE = 500

# ============================================================================
# RUN STATE TRACKING - For debugging via /scheduler-status endpoint
# ============================================================================
class SchedulerState:
    """Tracks scheduler run history for debugging."""

    def __init__(self):
        self.last_run_start: Optional[datetime] = None
        self.last_run_end: Optional[datetime] = None
        self.last_run_status: Optional[str] = None  # "success", "failed", "running"
        self.last_run_updated: int = 0
        self.last_run_failed: int = 0
        self.last_run_error: Optional[str] = None
        self.total_runs: int = 0
        self.total_successful: int = 0
        self.total_failed: int = 0
        # Keep last 5 runs for history
        self.run_history: list = []

    def start_run(self):
        self.last_run_start = datetime.now()
        self.last_run_end = None
        self.last_run_status = "running"
        self.last_run_error = None
        self.last_run_updated = 0
        self.last_run_failed = 0

    def complete_run(self, updated: int, failed: int):
        self.last_run_end = datetime.now()
        self.last_run_status = "success"
        self.last_run_updated = updated
        self.last_run_failed = failed
        self.total_runs += 1
        self.total_successful += 1
        self._add_to_history("success", updated, failed, None)

    def fail_run(self, error: str):
        self.last_run_end = datetime.now()
        self.last_run_status = "failed"
        self.last_run_error = error
        self.total_runs += 1
        self.total_failed += 1
        self._add_to_history("failed", 0, 0, error)

    def _add_to_history(self, status: str, updated: int, failed: int, error: Optional[str]):
        entry = {
            "start": self.last_run_start.isoformat() if self.last_run_start else None,
            "end": self.last_run_end.isoformat() if self.last_run_end else None,
            "status": status,
            "updated": updated,
            "failed": failed,
            "error": error[:200] if error else None,  # Truncate long errors
        }
        self.run_history.insert(0, entry)
        self.run_history = self.run_history[:5]  # Keep only last 5

    def to_dict(self):
        return {
            "last_run": {
                "start": self.last_run_start.isoformat() if self.last_run_start else None,
                "end": self.last_run_end.isoformat() if self.last_run_end else None,
                "status": self.last_run_status,
                "stocks_updated": self.last_run_updated,
                "stocks_failed": self.last_run_failed,
                "error": self.last_run_error,
            },
            "totals": {
                "total_runs": self.total_runs,
                "successful_runs": self.total_successful,
                "failed_runs": self.total_failed,
            },
            "history": self.run_history,
        }

# Global state instance
scheduler_state = SchedulerState()


def update_us_prices_job():
    """
    Update current prices for US stocks in rotating batches.

    Runs every 30 minutes during US market hours (9:00 AM - 4:00 PM ET).
    Updates oldest-updated stocks first, cycling through all stocks.
    With ~3,135 stocks and 500 per batch, full rotation takes ~7 runs (~3.5 hours).

    This is a synchronous function that runs in BackgroundScheduler's thread pool.
    Async FinnhubService calls are wrapped in asyncio.run() since we're in a
    separate thread from Uvicorn's event loop.
    """
    settings = get_settings()

    if not settings.us_stocks_enabled or not settings.finnhub_api_key:
        print("[SCHEDULER] Skipped: US stocks disabled or no API key", flush=True)
        return

    # Track run state for debugging
    scheduler_state.start_run()

    print("[SCHEDULER] Starting scheduled US price update (rotating batch)", flush=True)
    logger.info("Starting scheduled US price update (rotating batch)")

    db = SessionLocal()

    try:
        from app.models.us_stock import USStock
        from app.services.finnhub_service import FinnhubService

        # Get stocks with oldest price updates first (rotating through all)
        # This ensures all stocks get updated eventually
        stocks = db.query(USStock).filter(
            USStock.stock_type == "Common Stock"
        ).order_by(
            USStock.last_price_update.asc().nullsfirst()
        ).limit(PRICE_UPDATE_BATCH_SIZE).all()

        if not stocks:
            print("[SCHEDULER] No stocks to update", flush=True)
            logger.info("No stocks to update")
            scheduler_state.complete_run(0, 0)
            return

        print(f"[SCHEDULER] Found {len(stocks)} stocks to update", flush=True)

        updated_count = 0
        failed_count = 0

        # Define async function to fetch prices
        async def fetch_prices():
            nonlocal updated_count, failed_count
            async with FinnhubService(settings.finnhub_api_key) as service:
                for i, stock in enumerate(stocks):
                    try:
                        quote = await service.get_quote(stock.symbol)
                        price = quote.get("current_price")

                        if price:
                            stock.current_price = price
                            stock.previous_close = quote.get("previous_close")
                            stock.change = quote.get("change")
                            stock.change_pct = quote.get("change_pct")
                            stock.last_price_update = datetime.now()

                            # Recalculate discount to sticker
                            if stock.sticker_price and stock.sticker_price > 0:
                                stock.discount_to_sticker = (
                                    (price - stock.sticker_price) / stock.sticker_price * 100
                                )
                            updated_count += 1
                        else:
                            # Still update timestamp so we don't retry immediately
                            stock.last_price_update = datetime.now()
                            failed_count += 1

                    except Exception as e:
                        print(f"[SCHEDULER] Failed {stock.symbol}: {e}", flush=True)
                        logger.warning(f"Failed to update price for {stock.symbol}: {e}")
                        failed_count += 1

                    # Progress log every 100 stocks
                    if (i + 1) % 100 == 0:
                        print(f"[SCHEDULER] Progress: {i + 1}/{len(stocks)} processed", flush=True)

                    await asyncio.sleep(0.1)  # Rate limiting

        # Run the async function in this thread's event loop
        # Safe because BackgroundScheduler runs jobs in separate threads
        asyncio.run(fetch_prices())

        db.commit()
        print(f"[SCHEDULER] Price update complete: {updated_count} updated, {failed_count} failed", flush=True)
        logger.info(f"Price update complete: {updated_count} updated, {failed_count} failed")

        # Record success
        scheduler_state.complete_run(updated_count, failed_count)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"[SCHEDULER] Price update job failed: {error_msg}", flush=True)
        logger.error(f"Price update job failed: {e}")
        db.rollback()

        # Record failure
        scheduler_state.fail_run(error_msg)

    finally:
        db.close()


def setup_scheduler():
    """Configure the scheduler jobs."""
    settings = get_settings()

    if not settings.us_stocks_enabled:
        print("[SCHEDULER] US stocks disabled, scheduler not starting", flush=True)
        logger.info("US stocks disabled, scheduler not starting")
        return False

    # US price updates - rotates through ALL stocks in batches
    # Every 30 min during market hours: 9 AM - 4 PM ET (Mon-Fri)
    # 500 stocks/batch = ~7 batches to cover all 3,135 stocks = ~3.5 hours for full rotation
    scheduler.add_job(
        update_us_prices_job,
        CronTrigger(
            hour="9-16",  # 9 AM to 4 PM
            minute="0,30",  # Every 30 minutes
            day_of_week="mon-fri",  # Weekdays only
            timezone="America/New_York"
        ),
        id="us_prices_update",
        name="US Stocks Price Update (Rotating)",
        replace_existing=True,
    )

    print(f"[SCHEDULER] Configured with {len(scheduler.get_jobs())} jobs", flush=True)
    logger.info(f"Scheduler configured with {len(scheduler.get_jobs())} jobs")
    return True


def start_scheduler():
    """Start the scheduler."""
    try:
        if setup_scheduler():
            scheduler.start()
            print("[SCHEDULER] Started successfully", flush=True)
            logger.info("Scheduler started")
    except Exception as e:
        print(f"[SCHEDULER] Failed to start: {e}", flush=True)
        logger.error(f"Failed to start scheduler: {e}")


def stop_scheduler():
    """Stop the scheduler."""
    try:
        scheduler.shutdown(wait=False)
        print("[SCHEDULER] Stopped", flush=True)
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")


def get_scheduler_state():
    """Get current scheduler state for debugging."""
    return scheduler_state.to_dict()


def trigger_price_update():
    """Manually trigger the price update job (for testing)."""
    print("[SCHEDULER] Manual trigger requested", flush=True)
    # Run in a thread to avoid blocking
    import threading
    thread = threading.Thread(target=update_us_prices_job)
    thread.start()
    return {"status": "triggered", "message": "Job started in background thread"}
