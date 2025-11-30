import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    MONGO_DB_URI: str
    MONGO_DB_TEST_URI: str
    ENVIRONMENT: str
    CELERY_BROKER_URL: str
    SECRET_API_KEY: str
    REDIS_URL: str
    RATE_LIMIT_MAX_REQUESTS: int
    RATE_LIMIT_WINDOW_SECONDS: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


logger.debug(f"MongoDB URI: {settings.MONGO_DB_URI}")
