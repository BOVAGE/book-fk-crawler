import logging
from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, status

from api.exceptions import BookNotFoundError
from api.schemas import (
    BookDetailResponse,
    BooksListResponse,
    ChangesListResponse,
    SortBy,
    SuccessResponse,
)
from api.services import BookService, ChangesService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

book_router = APIRouter()
changes_router = APIRouter()

book_service = BookService()
changes_service = ChangesService()


@book_router.get("", response_model=BooksListResponse, status_code=status.HTTP_200_OK)
async def get_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    rating: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[SortBy] = Query(
        None,
        description="Sort field with Django-style prefix. Use '-' for descending order",
    ),
):
    """Get paginated list of books with optional filtering."""
    try:
        data = await book_service.get_books_paginated(
            page=page,
            page_size=page_size,
            category=category,
            rating=rating,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
        )

        return SuccessResponse(
            status="success", message="Books retrieved successfully", data=data
        )

    except Exception as e:
        logger.error(f"Error retrieving books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve books",
        )


@book_router.get(
    "/{book_id}", response_model=BookDetailResponse, status_code=status.HTTP_200_OK
)
async def get_book_by_id(book_id: PydanticObjectId):
    """Get a specific book by ID."""
    try:
        data = await book_service.get_book_by_id(book_id)

        return SuccessResponse(
            status="success", message="Book retrieved successfully", data=data
        )

    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    except Exception as e:
        logger.error(f"Error retrieving book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve book",
        )


@changes_router.get(
    "", response_model=ChangesListResponse, status_code=status.HTTP_200_OK
)
async def get_recent_changes(
    limit: int = Query(50, ge=1, le=100),
    hours_back: int = Query(24, ge=1, le=168),  # Max 1 week
    field: Optional[str] = None,
):
    """Get recent book changes."""
    try:
        data = await changes_service.get_recent_changes(
            limit=limit, hours_back=hours_back, field=field
        )

        return SuccessResponse(
            status="success", message="Changes retrieved successfully", data=data
        )

    except Exception as e:
        logger.error(f"Error retrieving changes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve changes",
        )
