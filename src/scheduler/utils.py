import json
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.main import crawl_all, init_db
from crawler.models import Book, ChangeLog
from typing import Dict, Any, Optional
from utilities.constants import SIGNIFICANT_CHANGE_THRESHOLD

logger = logging.getLogger(__name__)


def save_report_to_file(report_data: Dict[str, Any], filename: str):
    """Save report data to JSON file."""
    with open(filename, "w") as f:
        json.dump(report_data, f, indent=2, default=str)


async def create_daily_report():
    """Create a comprehensive daily report of all changes."""
    db_client = await init_db()

    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_changes = (
        await ChangeLog.find(ChangeLog.changed_at >= yesterday)
        .sort(-ChangeLog.changed_at)
        .to_list()
    )

    new_books = await Book.find(Book.created_at >= yesterday).to_list()

    report_data = {
        "report_date": datetime.utcnow().isoformat(),
        "period": "24_hours",
        "summary": {
            "total_changes": len(recent_changes),
            "new_books": len(new_books),
            "change_types": {},
        },
        "changes": [],
        "new_books": [],
    }

    for change in recent_changes:
        await change.fetch_link(ChangeLog.book)

        change_data = {
            "book_title": change.book.title,
            "book_id": str(change.book.id),
            "field_changed": change.field_changed,
            "old_value": change.old_value,
            "new_value": change.new_value,
            "changed_at": change.changed_at.isoformat(),
        }
        report_data["changes"].append(change_data)

        # Count change types
        field = change.field_changed
        if field not in report_data["summary"]["change_types"]:
            report_data["summary"]["change_types"][field] = 0
        report_data["summary"]["change_types"][field] += 1

    for book in new_books:
        await book.fetch_link(Book.category)

        book_data = {
            "book_id": str(book.id),
            "title": book.title,
            "name": book.name,
            "category": book.category.name,
            "currency": book.currency,
            "price_with_tax": float(book.price_with_tax),
            "price_without_tax": float(book.price_without_tax),
            "created_at": book.created_at.isoformat(),
        }
        report_data["new_books"].append(book_data)

    report_filename = f"daily_report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"

    save_report_to_file(report_data, report_filename)
    logger.info(f"📄 Report data ready: {report_data['summary']}")
    await db_client.close()

    return {
        "report_filename": report_filename,
        "changes_count": len(recent_changes),
        "new_books_count": len(new_books),
        "status": "success",
    }


async def run_scraping_process(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Main async function that orchestrates the scraping process.
    """
    start_time = datetime.utcnow()

    db_client = await init_db()

    initial_book_count = await Book.find().count()
    initial_change_count = await ChangeLog.find().count()

    logger.info(f"📊 Starting scrape - Current books: {initial_book_count}")

    await crawl_all(limit=limit)

    final_book_count = await Book.find().count()
    final_change_count = await ChangeLog.find().count()

    new_books = final_book_count - initial_book_count
    new_changes = final_change_count - initial_change_count

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    summary = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "total_books": final_book_count,
        "new_books_added": new_books,
        "changes_detected": new_changes,
        "status": "success",
    }

    logger.info(f"📈 Scrape Summary: {summary}")

    if new_books > 0 or new_changes > SIGNIFICANT_CHANGE_THRESHOLD:
        await send_change_alert(summary)
    await db_client.close()
    return summary


async def send_change_alert(summary: Dict[str, Any]):
    """Send alert when significant changes are detected."""
    try:
        logger.info(f"🚨 Significant changes detected, sending alert...")

        alert_msg = f"""
        📚 Book Scraping Alert - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
        
        Summary:
        - New books added: {summary['new_books_added']}
        - Changes detected: {summary['changes_detected']}
        - Total books: {summary['total_books']}
        - Duration: {summary['duration_seconds']:.2f} seconds
        
        Check the database for detailed change logs.
        """

        logger.info(alert_msg)

        # TODO: Implement actual email/notification service

    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


async def send_failure_alert(error_message: str):
    """Send alert when scraping fails."""
    logger.error(f"🔥 SCRAPING FAILED: {error_message}, sending alert...")
    # TODO: Implement actual email/notification service
