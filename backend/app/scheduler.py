"""APScheduler setup for automated background tasks.

Note: Fundamental data now comes from SimFin bulk import.
Scheduler only handles live price updates.
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


async def update_us_prices_job():
    """
    Update current prices for US stocks.

    Runs every 30 minutes during US market hours (9:30 AM - 4:00 PM ET).
    Only updates prices, not fundamentals (which come from SimFin).
    """
    settings = get_settings()

    if not settings.us_stocks_enabled or not settings.finnhub_api_key:
        return

    logger.info("Starting scheduled US price update")

    db = SessionLocal()

    try:
        from app.models.us_stock import USStock
        from app.services.finnhub_service import FinnhubService

        # Get S&P 500 stocks for price updates (most important)
        stocks = db.query(USStock).filter(
            USStock.is_sp500 == True
        ).all()

        if not stocks:
            return

        async with FinnhubService(settings.finnhub_api_key) as service:
            for stock in stocks:
                try:
                    quote = await service.get_quote(stock.symbol)
                    stock.current_price = quote.get("current_price")
                    stock.previous_close = quote.get("previous_close")
                    stock.change = quote.get("change")
                    stock.change_pct = quote.get("change_pct")
                    stock.last_price_update = datetime.now()

                    # Recalculate discount
                    if stock.sticker_price and stock.current_price and stock.sticker_price > 0:
                        stock.discount_to_sticker = (
                            (stock.current_price - stock.sticker_price) / stock.sticker_price * 100
                        )

                except Exception as e:
                    logger.warning(f"Failed to update price for {stock.symbol}: {e}")

                await asyncio.sleep(0.1)

        db.commit()
        logger.info(f"Updated prices for {len(stocks)} S&P 500 stocks")

    except Exception as e:
        logger.error(f"Price update job failed: {e}")

    finally:
        db.close()


def setup_scheduler():
    """Configure and start the scheduler."""
    settings = get_settings()

    if not settings.us_stocks_enabled:
        logger.info("US stocks disabled, scheduler not starting")
        return

    # US price updates (every 30 minutes during US market hours: 9:30 AM - 4:00 PM ET)
    scheduler.add_job(
        update_us_prices_job,
        CronTrigger(
            hour="9-16",  # 9 AM to 4 PM
            minute="0,30",  # Every 30 minutes
            day_of_week="mon-fri",  # Weekdays only
            timezone="America/New_York"
        ),
        id="us_prices_update",
        name="US Stocks Price Update",
        replace_existing=True,
    )

    logger.info(f"Scheduler configured with {len(scheduler.get_jobs())} jobs")


def start_scheduler():
    """Start the scheduler."""
    try:
        setup_scheduler()
        scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def stop_scheduler():
    """Stop the scheduler."""
    try:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
