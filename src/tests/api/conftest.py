from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, List

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager

from api import app
from config import settings
from src.models import Book, BookCategory, ChangeLog, Metadata


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for testing API endpoints."""
    async with LifespanManager(app) as manager:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=manager.app), base_url="http://test"
        ) as ac:
            yield ac


@pytest_asyncio.fixture
def api_headers():
    """Standard API headers with authentication."""
    return {"x-api-key": settings.SECRET_API_KEY, "Content-Type": "application/json"}


@pytest_asyncio.fixture
async def sample_categories() -> List[BookCategory]:
    """Create sample book categories for testing."""
    categories = [
        BookCategory(name="Fiction", description="Fictional books"),
        BookCategory(name="Science", description="Science books"),
        BookCategory(name="History", description="Historical books"),
    ]

    inserted_categories = []
    for category in categories:
        await category.insert()
        inserted_categories.append(category)

    return inserted_categories


@pytest_asyncio.fixture
async def sample_books(sample_categories) -> List[Book]:
    """Create sample books for testing."""
    fiction_category = sample_categories[0]
    science_category = sample_categories[1]

    books_data = [
        {
            "title": "test-book-1",
            "name": "The Great Test",
            "description": "A great book for testing",
            "category": fiction_category,
            "currency": "£",
            "price_with_tax": Decimal("19.99"),
            "price_without_tax": Decimal("16.66"),
            "availability": "In stock (22 available)",
            "no_of_reviews": 15,
            "no_of_ratings": 4,
            "cover_image_url": "https://example.com/image1.jpg",
            "metadata": Metadata(
                crawled_at=datetime.utcnow(),
                status="crawled",
                source_url="https://example.com/book1",
                content_hash="abc123",
            ),
        },
        {
            "title": "test-book-2",
            "name": "Science for Dummies",
            "description": "Learn science the easy way",
            "category": science_category,
            "currency": "£",
            "price_with_tax": Decimal("25.50"),
            "price_without_tax": Decimal("21.25"),
            "availability": "In stock (5 available)",
            "no_of_reviews": 8,
            "no_of_ratings": 5,
            "cover_image_url": "https://example.com/image2.jpg",
            "metadata": Metadata(
                crawled_at=datetime.utcnow(),
                status="crawled",
                source_url="https://example.com/book2",
                content_hash="def456",
            ),
        },
        {
            "title": "test-book-3",
            "name": "Expensive Book",
            "description": "Very costly book",
            "category": fiction_category,
            "currency": "£",
            "price_with_tax": Decimal("99.99"),
            "price_without_tax": Decimal("83.33"),
            "availability": "Out of stock",
            "no_of_reviews": 2,
            "no_of_ratings": 3,
            "cover_image_url": "https://example.com/image3.jpg",
            "metadata": Metadata(
                crawled_at=datetime.utcnow(),
                status="crawled",
                source_url="https://example.com/book3",
                content_hash="ghi789",
            ),
        },
    ]

    books = []
    for book_data in books_data:
        book = Book(**book_data)
        await book.insert()
        books.append(book)

    return books


@pytest_asyncio.fixture
async def sample_changes(sample_books) -> List[ChangeLog]:
    """Create sample change logs for testing."""
    book1, book2 = sample_books[0], sample_books[1]

    changes = [
        ChangeLog(
            book=book1,
            field_changed="price_with_tax",
            old_value="15.99",
            new_value="19.99",
            changed_at=datetime.utcnow(),
        ),
        ChangeLog(
            book=book2,
            field_changed="availability",
            old_value="In stock (10 available)",
            new_value="In stock (5 available)",
            changed_at=datetime.utcnow(),
        ),
    ]

    inserted_changes = []
    for change in changes:
        await change.insert()
        inserted_changes.append(change)

    return inserted_changes
