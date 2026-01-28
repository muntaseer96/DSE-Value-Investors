"""APScheduler setup for automated background tasks.

Note: Fundamental data now comes from SimFin bulk import.
Scheduler handles live price updates for ALL stocks in rotating batches.
"""
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Batch size for price updates (respects Finnhub 60 calls/min rate limit)
# With 0.1s delay between calls, 500 stocks takes ~50 seconds
PRICE_UPDATE_BATCH_SIZE = 500


async def update_us_prices_job():
    """
    Update current prices for US stocks in rotating batches.

    Runs every 30 minutes during US market hours (9:30 AM - 4:00 PM ET).
    Updates oldest-updated stocks first, cycling through all stocks.
    With ~3,135 stocks and 500 per batch, full rotation takes ~7 runs (~3.5 hours).
    """
    settings = get_settings()

    if not settings.us_stocks_enabled or not settings.finnhub_api_key:
        return

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
            logger.info("No stocks to update")
            return

        updated_count = 0
        failed_count = 0

        async with FinnhubService(settings.finnhub_api_key) as service:
            for stock in stocks:
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
                    logger.warning(f"Failed to update price for {stock.symbol}: {e}")
                    failed_count += 1

                await asyncio.sleep(0.1)  # Rate limiting

        db.commit()
        print(f"[SCHEDULER] Price update complete: {updated_count} updated, {failed_count} failed", flush=True)
        logger.info(f"Price update complete: {updated_count} updated, {failed_count} failed")

    except Exception as e:
        print(f"[SCHEDULER] Price update job failed: {e}", flush=True)
        logger.error(f"Price update job failed: {e}")

    finally:
        db.close()


def setup_scheduler():
    """Configure and start the scheduler."""
    settings = get_settings()

    if not settings.us_stocks_enabled:
        logger.info("US stocks disabled, scheduler not starting")
        return

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


def start_scheduler():
    """Start the scheduler."""
    try:
        setup_scheduler()
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
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
