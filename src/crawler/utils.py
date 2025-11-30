import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from crawler.fetcher import fetch_html
from crawler.parser import _parse_book_details
from models import Book, BookCategory, ChangeLog, Metadata
from utilities.utils import detect_changes, generate_hash

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def save_changes_log(
    existing_book: Book, changes: Dict[str, Dict[str, Optional[str]]]
):
    """Save change logs for the detected changes"""
    for field, change_info in changes.items():
        try:
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
            logger.debug(
                f"Saved change log for {field}: {change_info['old']} -> {change_info['new']}"
            )
        except Exception as e:
            logger.error(f"Failed to save change log for {field}: {e}")


async def get_or_create_category(category_name: str) -> BookCategory:
    """Get existing category or create new one"""
    if not category_name or not category_name.strip():
        logger.warning("Empty category name, using 'Unknown'")
        category_name = "Unknown"

    category = await BookCategory.find_one(BookCategory.name == category_name)
    if not category:
        logger.info(f"Creating new category: {category_name}")
        category = BookCategory(name=category_name)
        await category.insert()
    return category


async def create_new_book(book_data: dict, category: BookCategory) -> Book:
    """Create a new book from parsed data"""
    title = book_data.get("title", "")
    current_hash = generate_hash(book_data)

    metadata = Metadata(
        crawled_at=datetime.utcnow(),
        status="crawled",
        source_url=book_data.get("source_url", ""),
        content_hash=current_hash,
    )

    book = Book(
        title=title,
        name=book_data.get("name", "Unknown"),
        description=book_data.get("description"),
        category=category,
        currency=book_data.get("currency", "£"),
        price_with_tax=Decimal(str(book_data.get("price_with_tax", 0))),
        price_without_tax=Decimal(str(book_data.get("price_without_tax", 0))),
        availability=book_data.get("availability", "Unknown"),
        no_of_reviews=book_data.get("no_of_reviews", 0),
        cover_image_url=book_data.get("image_url"),
        no_of_ratings=book_data.get("no_of_ratings", 0),
        raw_html=book_data.get("raw_html"),
        metadata=metadata,
    )

    await book.insert()
    return book


async def update_existing_book(
    existing_book: Book, book_data: dict, changes: dict
) -> Book:
    """Update existing book with new data"""
    await save_changes_log(existing_book, changes)

    # Apply changes
    for field, change_info in changes.items():
        try:
            setattr(existing_book, field, change_info["new"])
        except Exception as e:
            logger.error(f"Failed to update field {field}: {e}")

    # Update metadata
    existing_book.raw_html = book_data.get("raw_html")
    existing_book.metadata.content_hash = generate_hash(book_data)
    existing_book.metadata.crawled_at = datetime.utcnow()
    existing_book.updated_at = datetime.utcnow()

    await existing_book.save()
    return existing_book


async def save_or_update_book(book_data: dict) -> Dict[str, int]:
    """Save or update book in the database"""
    stats = {"added": 0, "updated": 0, "errors": 0}

    try:
        # Handle category
        category_name = book_data.get("category", "Unknown")
        category = await get_or_create_category(category_name)

        title = book_data.get("title", "")
        if not title:
            logger.error("Book has no title, skipping")
            stats["errors"] = 1
            return stats

        existing_book = await Book.find_one(Book.title == title)
        current_hash = generate_hash(book_data)

        if not existing_book:
            logger.info(f"Inserting new book: {title}")
            await create_new_book(book_data, category)
            stats["added"] = 1
            return stats

        # Check for changes
        existing_data = existing_book.model_dump()
        logger.debug(f"existing book hash: {existing_book.metadata.content_hash}")
        logger.debug(f"new book data hash: {current_hash}")

        if existing_book.metadata.content_hash == current_hash:
            logger.info(f"No changes detected for book: {title}")
            return stats

        changes = detect_changes(existing_data, book_data)
        if not changes:
            logger.info(f"No changes detected for book: {title}")
            return stats

        logger.info(f"Updating book '{title}' with changes: {list(changes.keys())}")
        await update_existing_book(existing_book, book_data, changes)
        stats["updated"] = 1

    except Exception as e:
        logger.error(f"Failed to save/update book: {e}", exc_info=True)
        stats["errors"] = 1

    return stats


async def process_book_url(book_url: str) -> Dict[str, Any]:
    """Process a single book URL and return results"""

    result = {
        "url": book_url,
        "success": False,
        "error": None,
        "stats": {"added": 0, "updated": 0, "errors": 0},
    }

    try:
        book_html = await fetch_html(book_url)
        book_data = _parse_book_details(book_html, book_url)

        if book_data:  # Only process if we got valid data
            stats = await save_or_update_book(book_data)
            result["stats"] = stats
            result["success"] = stats["errors"] == 0
        else:
            result["error"] = "Failed to parse book data"
            result["stats"]["errors"] = 1

    except Exception as e:
        logger.error(f"Failed to process book {book_url}: {e}")
        result["error"] = str(e)
        result["stats"]["errors"] = 1

    return result


async def process_page_books(book_urls: list[str]) -> Dict[str, int]:
    """Process all books on a page"""
    total_stats = {"added": 0, "updated": 0, "errors": 0, "processed": 0}

    for book_url in book_urls:
        result = await process_book_url(book_url)

        # Aggregate stats
        for key in ["added", "updated", "errors"]:
            total_stats[key] += result["stats"][key]

        if result["success"]:
            total_stats["processed"] += 1

        # Log progress
        if result["success"]:
            logger.debug(f"✅ Processed: {book_url}")
        else:
            logger.warning(f"❌ Failed: {book_url} - {result['error']}")

    return total_stats
