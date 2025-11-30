from beanie import init_beanie
from pymongo import AsyncMongoClient

from config import settings
from models import Book, BookCategory, ChangeLog, CrawlSession


async def init_db() -> AsyncMongoClient:
    """Initialize the database connection and Beanie ODM."""
    client = AsyncMongoClient(settings.MONGO_DB_URI)

    await init_beanie(
        database=client.get_default_database(),
        document_models=[Book, BookCategory, ChangeLog, CrawlSession],
    )
    return client
