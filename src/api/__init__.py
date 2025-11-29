import os
import sys

# print(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import settings
from fastapi import FastAPI, status, Request, Depends
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from api.routes import book_router, changes_router
from api.schemas import SuccessResponse, ErrorResponse
from fastapi.middleware.cors import CORSMiddleware
from crawler.models import Book, BookCategory, ChangeLog
from contextlib import asynccontextmanager
from pymongo import AsyncMongoClient
from beanie import init_beanie
from api.dependencies import get_api_key, get_api_key_from_header
import logging
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server is starting...")
    db_uri = (
        settings.MONGO_DB_TEST_URI
        if settings.ENVIRONMENT == "test"
        else settings.MONGO_DB_URI
    )
    db_client = AsyncMongoClient(db_uri)

    await init_beanie(
        database=db_client.get_default_database(),
        document_models=[Book, BookCategory, ChangeLog],
    )
    logger.info("Database initialized successfully")
    redis_connection = redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(
        redis_connection, prefix="fastapi-limiter", identifier=get_api_key_from_header
    )

    yield

    # Cleanup on shutdown
    await db_client.close()
    await FastAPILimiter.close()
    logger.info("Server is stopping")


version = "v1"

app = FastAPI(
    title="Books FK Crawler API",
    description="A RESTful API for viewing crawled books",
    version=version,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Overrides FastAPI's default validation handler to use JSend fail format."""

    # Transform errors into a dictionary where the field is the key and the messages are a list
    error_details = {}
    for error in exc.errors():
        field = ".".join(map(str, error["loc"]))
        if field not in error_details:
            error_details[field] = []
        error_details[field].append(error["msg"])

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorResponse(error=error_details).model_dump(),
    )


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_error(request, exc):
    logger.debug(exc, dir(exc), type(exc))
    logger.debug("===" * 30)
    logger.debug(exc.detail)
    logger.debug("===" * 30)

    return JSONResponse(
        content={
            "status": "error",
            "message": f"{exc.detail}"
            or "The resource you are looking for does not exist",
        },
        status_code=status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_server_error(request, exc):

    return JSONResponse(
        content={"status": "error", "message": "Oops! Something went wrong"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.exception_handler(HTTPException)
async def generic_http_exception_handler(request: Request, exc: HTTPException):
    """Handles all HTTPException errors and formats them in JSend style."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail or "An error occurred"},
    )


if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
elif settings.ENVIRONMENT == "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

app.include_router(
    book_router,
    prefix=f"/api/{version}/books",
    tags=["books"],
    dependencies=[
        Depends(get_api_key),
        Depends(
            RateLimiter(
                times=settings.RATE_LIMIT_MAX_REQUESTS,
                seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            )
        ),
    ],
)
app.include_router(
    changes_router,
    prefix=f"/api/{version}/changes",
    tags=["changes"],
    dependencies=[
        Depends(get_api_key),
        Depends(
            RateLimiter(
                times=settings.RATE_LIMIT_MAX_REQUESTS,
                seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            )
        ),
    ],
)
