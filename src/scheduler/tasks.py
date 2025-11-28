import os
import sys
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import shared_task

from scheduler.utils import (
    run_scraping_process,
    send_failure_alert,
    create_daily_report,
)


logger = logging.getLogger(__name__)


@shared_task
def execute_scrape():
    """
    Task that runs the web scraping process.
    This is the entry point called by Celery Beat or can be invoked manually.
    """
    logger.info("🕒 Starting scrape task...")

    try:
        result = asyncio.run(run_scraping_process())
        logger.info(f"✅ Scrape completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Scrape failed: {str(e)}", exc_info=True)
        asyncio.run(send_failure_alert(str(e)))
        raise


@shared_task
def generate_daily_change_report():
    """Generate and save daily change report."""
    logger.info("📊 Generating daily change report...")

    try:
        result = asyncio.run(create_daily_report())
        logger.info(f"✅ Daily report generated: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Daily report generation failed: {str(e)}", exc_info=True)
        raise
