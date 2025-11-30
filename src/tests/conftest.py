import os
import sys

import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from config import settings
from src.models import Book, BookCategory, ChangeLog, CrawlSession


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Setup database for each test function"""
    # Initialize database connection for this test
    print("===" * 30)
    print("Setting up test database...")
    client = AsyncMongoClient(settings.MONGO_DB_TEST_URI)

    await init_beanie(
        database=client.get_default_database(),
        document_models=[Book, BookCategory, ChangeLog, CrawlSession],
    )

    # Clear all collections
    for model in [Book, BookCategory, ChangeLog, CrawlSession]:
        try:
            await model.delete_all()
        except Exception:
            pass
    print("Test database setup complete.")
    print("===" * 30)
    yield client

    # Cleanup
    for model in [Book, BookCategory, ChangeLog, CrawlSession]:
        try:
            await model.delete_all()
        except Exception:
            pass

    await client.close()
