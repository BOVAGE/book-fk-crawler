import logging
from datetime import datetime, timedelta
from typing import Optional

from models import CrawlSession, CrawlStatus

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SimpleCrawlManager:
    """Simple crawl state manager"""

    def __init__(self):
        self.session: Optional[CrawlSession] = None

    async def start_session(self, limit: Optional[int] = None) -> str:
        """Start a new crawl session"""

        self.session = CrawlSession(
            start_time=datetime.utcnow(),
            target_pages=limit,
            status=CrawlStatus.RUNNING,
        )

        await self.session.insert()
        logger.info(f"🚀 Started crawl session: {self.session.session_id}")
        return self.session.session_id

    async def resume_latest_failed_session(self) -> bool:
        """Resume the most recent failed session"""
        failed_session = (
            await CrawlSession.find(CrawlSession.status == CrawlStatus.FAILED)
            .sort(-CrawlSession.start_time)
            .first_or_none()
        )

        if not failed_session:
            logger.info("No failed session to resume")
            return False

        if failed_session.start_time < datetime.utcnow() - timedelta(hours=24):
            logger.info("Failed session too old to resume")
            return False

        self.session = failed_session
        self.session.status = CrawlStatus.RUNNING
        self.session.updated_at = datetime.utcnow()
        self.session.error_message = None
        await self.session.save()

        logger.info(
            f"🔄 Resumed session {failed_session.session_id} from page {failed_session.last_completed_page + 1}"
        )
        return True

    async def update_progress(
        self,
        completed_page: int,
        books_on_page: int,
        books_added: int = 0,
        books_updated: int = 0,
    ):
        """Update session progress"""
        if not self.session:
            return

        self.session.last_completed_page = completed_page
        self.session.total_books_processed += books_on_page
        self.session.books_added += books_added
        self.session.books_updated += books_updated
        self.session.updated_at = datetime.utcnow()

        await self.session.save()
        logger.debug(f"Updated progress: page {completed_page}, {books_on_page} books")

    async def complete_session(self, success: bool = True, error: str = None):
        """Mark session as completed or failed"""
        if not self.session:
            logger.warning("No active session to complete")
            return
        if success and error:
            raise AssertionError("Cannot have error message on successful completion")

        self.session.end_time = datetime.utcnow()
        self.session.status = CrawlStatus.COMPLETED if success else CrawlStatus.FAILED
        self.session.updated_at = datetime.utcnow()

        if error:
            self.session.error_message = error

        await self.session.save()

        duration = (self.session.end_time - self.session.start_time).total_seconds()
        status_emoji = "✅" if success else "❌"

        logger.info(
            f"{status_emoji} Session {self.session.session_id} {'completed' if success else 'failed'} "
            f"in {duration:.1f}s - {self.session.total_books_processed} books processed"
        )

    def get_resume_page(self) -> int:
        """Get the page to resume from"""
        return self.session.last_completed_page + 1 if self.session else 1
