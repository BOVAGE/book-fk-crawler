import os
import sys

# print(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import logging
from crawler.fetcher import fetch_html
from crawler.parser import parse_book_list, parse_book_details
from pymongo import AsyncMongoClient
from beanie import init_beanie
from datetime import datetime
from decimal import Decimal
from crawler.models import Book, BookCategory, Metadata, ChangeLog, CrawlSession
from config import settings
from utilities.utils import generate_hash, detect_changes
from utilities.constants import BASE_PAGE_URL
from typing import Dict, Optional, Any
from crawler.manager import SimpleCrawlManager
import httpx
import argparse


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def save_changes_log(
    existing_book: Book, changes: Dict[str, Dict[str, Optional[str]]]
):
    """Save change logs for the detected changes"""
    for field, change_info in changes.items():
        change_log = ChangeLog(
            book=existing_book,
            field_changed=field,
            old_value=(
                str(change_info["old"]) if change_info["old"] is not None else None
            ),
            new_value=(
                str(change_info["new"]) if change_info["new"] is not None else None
            ),
        )
        await change_log.insert()


async def save_or_update_book(book_data: dict) -> Dict[str, int]:
    """Save or update book in the database"""
    category_name = book_data["category"]
    category = await BookCategory.find_one(BookCategory.name == category_name)
    if not category:
        logger.info(f"Creating new category: {category_name}")
        category = BookCategory(name=category_name)
        await category.insert()
    title = book_data.get("title", "")
    existing_book = await Book.find_one(Book.title == title)
    current_hash = generate_hash(book_data)
    stats = {"added": 0, "updated": 0}
    if not existing_book:
        logger.info(f"Inserting new book: {title}")
        metadata = Metadata(
            scraped_at=datetime.utcnow(),
            status="scraped",
            source_url=book_data.get("source_url", ""),
            content_hash=current_hash,
        )
        book = Book(
            title=title,
            name=book_data.get("name", ""),
            description=book_data.get("description", ""),
            category=category,
            currency=book_data.get("currency"),
            price_with_tax=Decimal(str(book_data.get("price_with_tax", 0))),
            price_without_tax=Decimal(str(book_data.get("price_without_tax", 0))),
            availability=book_data.get("availability"),
            no_of_reviews=book_data.get("no_of_reviews", 0),
            cover_image_url=book_data.get("image_url"),
            no_of_ratings=book_data.get("no_of_ratings", 0),
            raw_html=book_data.get("raw_html", ""),
            metadata=metadata,
        )
        await book.insert()
        stats["added"] = 1
        return stats

    existing_data = existing_book.model_dump()
    logger.debug(f"existing book hash: {existing_book.metadata.content_hash}")
    logger.debug(f"new book data hash: {current_hash}")
    if existing_book.metadata.content_hash == current_hash:
        logger.info(f"No changes detected for book: {title}, hash matches.")
        return stats
    changes = detect_changes(existing_data, book_data)

    if not changes:
        logger.info(f"No changes detected for book: {title}")
        return stats

    await save_changes_log(existing_book, changes)
    logger.info(f"Saved change log for book: {title}")

    for field, change_info in changes.items():
        setattr(existing_book, field, change_info["new"])

    existing_book.raw_html = book_data.get("raw_html", "")
    logger.info(
        f"Updated HTML snapshot for book '{title}' due to changes in: {list(changes.keys())}"
    )

    existing_book.metadata.content_hash = current_hash
    existing_book.metadata.scraped_at = datetime.utcnow()
    existing_book.updated_at = datetime.utcnow()
    await existing_book.save()
    logger.info(f"Updated book '{title}' with changes: {list(changes.keys())}")

    stats["updated"] = 1
    return stats


async def init_db() -> AsyncMongoClient:
    """Initialize the database connection and Beanie ODM."""
    client = AsyncMongoClient(settings.MONGO_DB_URI)

    await init_beanie(
        database=client.get_default_database(),
        document_models=[Book, BookCategory, ChangeLog, CrawlSession],
    )
    return client


async def crawl_page(manager: SimpleCrawlManager, page: int) -> Dict[str, Any]:
    """Crawl a page"""
    url = BASE_PAGE_URL.format(page)
    logger.info(
        f"[Session {manager.session.session_id if manager.session else 'None'}] Crawling page {page}: {url}"
    )

    html = await fetch_html(url)
    book_urls = parse_book_list(html)

    books_processed = 0
    total_added = 0
    total_updated = 0

    for book_url in book_urls:
        try:
            book_html = await fetch_html(book_url)
            book_data = parse_book_details(book_html, book_url)
            logger.debug(f"Book found: {book_data}")
            stats = await save_or_update_book(book_data)
            total_added += stats["added"]
            total_updated += stats["updated"]
            books_processed += 1
        except Exception as e:
            logger.error(f"!!Failed to parse book:{book_url}", exc_info=True)
            continue

    await manager.update_progress(
        completed_page=page,
        books_on_page=books_processed,
        books_added=total_added,
        books_updated=total_updated,
    )

    return {
        "page": page,
        "books_processed": books_processed,
        "books_added": total_added,
        "books_updated": total_updated,
        "status": "success",
    }


async def crawl_all(*, limit: Optional[int] = None, auto_resume: bool = True):
    """Crawl all pages up to the limit. If limit is None, crawl until no more pages."""
    manager = SimpleCrawlManager()
    resumed = False
    if auto_resume:
        resumed = await manager.resume_latest_failed_session()

    if not resumed:
        await manager.start_session(limit)

    start_page = manager.get_resume_page()
    page = start_page

    logger.info(
        f"🎯 {'Resuming' if resumed else 'Starting'} crawl from page: {start_page}"
    )

    while limit is None or page <= limit:
        try:
            await crawl_page(manager, page)
            page += 1
        except Exception as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                logger.error(f"[Crawler] Page {page} does not exist. Stopping.", e)
                break
            else:
                logger.error(f"[Crawler] ❌ Unexpected error on page {page}: {str(e)}")
                await manager.complete_session(success=False, error=str(e))
                raise e
    logger.info(f"Handled {manager.session.total_books_processed} books.")
    await manager.complete_session(success=True)

    return {
        "session_id": manager.session.session_id,
        "status": "completed",
        "pages_processed": page - start_page,
        "total_books": manager.session.total_books_processed,
        "books_added": manager.session.books_added,
        "books_updated": manager.session.books_updated,
        "resumed": resumed,
    }


async def main():
    """Main function that runs both initialization and crawling in the same event loop."""
    parser = argparse.ArgumentParser(description="Web crawler for books.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of pages to crawl. Defaults to no limit.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the latest failed session if available.",
        default=True,
    )

    args = parser.parse_args()
    limit = args.limit
    auto_resume = args.resume
    logger.info(f"Starting crawler with limit={limit}, auto_resume={auto_resume}")

    await init_db()
    await crawl_all(limit=limit, auto_resume=auto_resume)


if __name__ == "__main__":
    asyncio.run(main())
