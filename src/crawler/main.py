import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from crawler.fetcher import fetch_html
from crawler.manager import SimpleCrawlManager
from crawler.parser import _parse_book_list
from crawler.utils import process_page_books
from db import init_db
from utilities.constants import BASE_PAGE_URL

logger = logging.getLogger(__name__)


async def crawl_page(manager: SimpleCrawlManager, page: int) -> Dict[str, Any]:
    """Crawl a single page and process all books on it.
    Raises error if page fetch fails. This error can be used to
    detect last page if it's not found (404).
    """
    url = BASE_PAGE_URL.format(page)
    logger.info(
        f"[Session {manager.session.session_id if manager.session else 'None'}] Crawling page {page}: {url}"
    )
    html = await fetch_html(url)

    try:
        book_urls = _parse_book_list(html)
        if not book_urls:
            logger.warning(f"No books found on page {page}")
            return {
                "page": page,
                "books_processed": 0,
                "books_added": 0,
                "books_updated": 0,
                "errors": 0,
                "status": "no_books",
            }

        logger.info(f"Found {len(book_urls)} books on page {page}")

        stats = await process_page_books(book_urls)

        await manager.update_progress(
            completed_page=page,
            books_on_page=stats["processed"],
            books_added=stats["added"],
            books_updated=stats["updated"],
        )

        return {
            "page": page,
            "books_processed": stats["processed"],
            "books_added": stats["added"],
            "books_updated": stats["updated"],
            "errors": stats["errors"],
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Failed to crawl page {page}: {e}", exc_info=True)
        return {
            "page": page,
            "books_processed": 0,
            "books_added": 0,
            "books_updated": 0,
            "errors": 1,
            "status": "error",
            "error": str(e),
        }


async def crawl_all(
    *, limit: Optional[int] = None, auto_resume: bool = True
) -> Dict[str, Any]:
    """Crawl all pages up to the limit with improved error handling"""
    manager = SimpleCrawlManager()
    resumed = False

    if auto_resume:
        resumed = await manager.resume_latest_failed_session()

    if not resumed:
        await manager.start_session(limit)

    start_page = manager.get_resume_page()
    page = start_page
    consecutive_errors = 0
    max_consecutive_errors = 3

    logger.info(
        f"🎯 {'Resuming' if resumed else 'Starting'} crawl from page: {start_page}"
    )

    while limit is None or page <= limit:
        try:
            result = await crawl_page(manager, page)

            if result["status"] == "success":
                consecutive_errors = 0
                page += 1
            elif result["status"] == "no_books":
                logger.info(f"No books found on page {page}, assuming end of catalog")
                break
            else:
                print("====" * 20)
                consecutive_errors += 1
                if (page == limit) or consecutive_errors >= max_consecutive_errors:
                    error_msg = f"Too many consecutive errors ({consecutive_errors}), stopping crawl"
                    logger.error(error_msg)
                    await manager.complete_session(success=False, error=error_msg)
                    # NOTE: Set to ensure the next try-except block
                    #       re-raises the error and ends the script
                    consecutive_errors = max_consecutive_errors
                    raise Exception(error_msg)
                page += 1

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info(f"Page {page} not found (404), end of catalog reached")
                break
            else:
                consecutive_errors += 1
                error_msg = f"HTTP {e.response.status_code} error on page {page}"
                logger.error(error_msg)

                if consecutive_errors >= max_consecutive_errors:
                    await manager.complete_session(success=False, error=error_msg)
                    raise
                page += 1

        except Exception as e:
            consecutive_errors += 1
            error_msg = f"Unexpected error on page {page}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            if consecutive_errors >= max_consecutive_errors:
                await manager.complete_session(success=False, error=error_msg)
                raise
            page += 1
    print(page, "====" * 20)
    logger.info(
        f"Crawl completed. Processed {manager.session.total_books_processed} books."
    )
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
    """Main function with improved argument handling"""
    parser = argparse.ArgumentParser(description="Robust web crawler for books")
    parser.add_argument("--limit", type=int, help="Limit pages to crawl")
    parser.add_argument(
        "--no-resume", action="store_true", help="Start fresh, don't resume"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    auto_resume = not args.no_resume
    logger.info(f"Starting crawler: limit={args.limit}, auto_resume={auto_resume}")

    try:
        await init_db()
        result = await crawl_all(limit=args.limit, auto_resume=auto_resume)
        logger.info(f"Crawl completed successfully: {result}")
    except Exception as e:
        logger.error(f"Crawl failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
