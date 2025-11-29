from typing import Optional, Annotated, Any

from pydantic import BaseModel, Field, field_validator

from beanie import Document, Indexed, Link
from datetime import datetime
from decimal import Decimal
from bson.decimal128 import Decimal128
from enum import Enum
import uuid


class BookCategory(Document):
    name: str
    description: Optional[str] = None


class Metadata(BaseModel):
    scraped_at: datetime
    status: str
    source_url: str
    content_hash: str


class Book(Document):
    title: str = Field(unique=True)
    name: str
    description: Optional[str] = None
    category: Link[BookCategory]
    currency: str
    price_with_tax: Annotated[Decimal, Indexed()]
    price_without_tax: Annotated[Decimal, Indexed()]
    availability: str
    no_of_reviews: Annotated[int, Indexed()]
    cover_image_url: Optional[str] = None
    no_of_ratings: Annotated[int, Indexed()]
    raw_html: Optional[str] = None
    metadata: Metadata
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    @field_validator("price_with_tax", "price_without_tax", mode="before")
    @classmethod
    def convert_decimal128(cls, v: Any) -> Decimal:
        if isinstance(v, Decimal128):
            return Decimal(str(v))
        return v


class ChangeLog(Document):
    book: Link[Book]
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime = datetime.utcnow()


class CrawlStatus(str, Enum):
    """Crawl session status"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlSession(Document):
    """Simple crawl session tracking"""

    session_id: uuid.UUID = Field(unique=True, default_factory=uuid.uuid4)  # UUID
    status: CrawlStatus = CrawlStatus.RUNNING

    # Progress tracking
    start_time: datetime
    end_time: Optional[datetime] = None
    last_completed_page: int = 0  # Last successfully completed page
    target_pages: Optional[int] = None

    # Statistics
    total_books_processed: int = 0
    books_added: int = 0
    books_updated: int = 0

    # Error info
    error_message: Optional[str] = None

    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
