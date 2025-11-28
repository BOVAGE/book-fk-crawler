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
from crawler.models import Book, BookCategory, Metadata, ChangeLog
from config import settings
from utilities.utils import generate_hash, detect_changes
from utilities.constants import BASE_PAGE_URL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


results = []


async def save_book(book_data: dict):
    category_name = book_data["category"]
    category = await BookCategory.find_one(BookCategory.name == category_name)
    if not category:
        logger.info(f"Creating new category: {category_name}")
        category = BookCategory(name=category_name)
        await category.insert()
    title = book_data.get("title", "")
    existing_book = await Book.find_one(Book.title == title)
    current_hash = generate_hash(book_data)

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
        return
    existing_data = existing_book.model_dump()
    logger.debug(f"existing book hash: {existing_book.metadata.content_hash}")
    logger.debug(f"new book data hash: {current_hash}")
    if existing_book.metadata.content_hash == current_hash:
        logger.info(f"No changes detected for book: {title}, hash matches.")
        return
    changes = detect_changes(existing_data, book_data)

    if not changes:
        logger.info(f"No changes detected for book: {title}")
        return

    # Log each change
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


async def init_db() -> AsyncMongoClient:
    """Initialize the database connection and Beanie ODM."""
    client = AsyncMongoClient(settings.MONGO_DB_URI)

    await init_beanie(
        database=client.get_default_database(),
        document_models=[Book, BookCategory, ChangeLog],
    )
    return client


async def crawl_page(page: int):
    url = BASE_PAGE_URL.format(page)
    logger.info(f"[Crawler] Fetching page: {url}")

    html = await fetch_html(url)
    book_urls = parse_book_list(html)

    for book_url in book_urls:
        try:
            book_html = await fetch_html(book_url)
            book_data = parse_book_details(book_html, book_url)
            logger.debug(f"Book found: {book_data}")
            await save_book(book_data)
            results.append(book_data)
        except Exception as e:
            logger.error(f"!!Failed to parse book:{book_url}", exc_info=True)


async def crawl_all(limit=None):
    page = 1

    while limit is None or page <= limit:
        try:
            await crawl_page(page)
            page += 1
        except Exception as e:
            print(f"[Crawler] Page {page} does not exist. Stopping.", e)
            break
    print(f"Handled {len(results)} books.")


async def main():
    """Main function that runs both initialization and crawling in the same event loop."""
    await init_db()
    await crawl_all(2)


if __name__ == "__main__":
    asyncio.run(main())
