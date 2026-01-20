"""APScheduler setup for automated background tasks."""
import asyncio
import logging
from datetime import datetime
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def scrape_us_stocks_job():
    """
    Scheduled job to scrape US stocks from Finnhub.

    Runs every 6 hours (configurable).
    Scrapes 500 stocks per run based on priority queue.
    """
    settings = get_settings()

    if not settings.us_stocks_enabled:
        logger.info("US stocks scraping is disabled")
        return

    if not settings.finnhub_api_key:
        logger.error("FINNHUB_API_KEY not configured, skipping US stocks scrape")
        return

    logger.info(f"Starting scheduled US stocks scrape (batch size: {settings.us_scrape_batch_size})")

    db = SessionLocal()

    try:
        from app.models.us_stock import USStock, USFinancialData
        from app.services.finnhub_service import FinnhubService
        from app.routers.us_stocks import _save_us_stock_data, _calculate_us_valuations

        # Get next batch of stocks to scrape
        # Priority: S&P 500 first, then never scraped, then oldest updates
        stocks = db.query(USStock).order_by(
            USStock.is_sp500.desc(),  # S&P 500 first
            USStock.last_fundamental_update.asc().nullsfirst(),  # Never scraped first
            USStock.scrape_priority.asc()  # Then by priority
        ).limit(settings.us_scrape_batch_size).all()

        if not stocks:
            logger.info("No US stocks to scrape")
            return

        symbols = [s.symbol for s in stocks]
        logger.info(f"Scraping {len(symbols)} US stocks: {symbols[:5]}...")

        success_count = 0
        fail_count = 0

        async with FinnhubService(settings.finnhub_api_key) as service:
            for i, symbol in enumerate(symbols):
                try:
                    data = await service.scrape_stock(symbol)
                    _save_us_stock_data(db, symbol, data)
                    _calculate_us_valuations(db, symbol)
                    success_count += 1

                    if (i + 1) % 50 == 0:
                        logger.info(f"Progress: {i + 1}/{len(symbols)} stocks scraped")

                except Exception as e:
                    logger.error(f"Error scraping {symbol}: {e}")
                    fail_count += 1

                # Small delay between stocks
                await asyncio.sleep(0.5)

        logger.info(f"Scheduled scrape complete: {success_count} success, {fail_count} failed")

    except Exception as e:
        logger.error(f"Scheduled US stocks scrape failed: {e}")

    finally:
        db.close()


async def update_us_prices_job():
    """
    Update current prices for US stocks.

    Runs more frequently (every hour during market hours).
    Only updates prices, not fundamentals.
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

    # US stocks fundamental scrape (every 6 hours)
    scheduler.add_job(
        scrape_us_stocks_job,
        IntervalTrigger(hours=settings.us_scrape_interval_hours),
        id="us_stocks_scrape",
        name="US Stocks Fundamental Scrape",
        replace_existing=True,
    )

    # US price updates (every hour during US market hours: 9:30 AM - 4:00 PM ET)
    # Using a cron trigger for market hours only
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
