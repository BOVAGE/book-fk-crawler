from fastapi import APIRouter, status, HTTPException, Query
from typing import Optional
from beanie import PydanticObjectId
from crawler.models import Book, BookCategory, ChangeLog
from datetime import datetime, timedelta
from api.schemas import (
    BooksListResponse,
    BookCategoryResponse,
    BooksListResponse,
    BookDetailResponse,
    ChangesListResponse,
    BooksListData,
    BookDetailData,
    BookFullDetail,
    BookPartialDetail,
    SuccessResponse,
    ChangesListData,
    ChangeLogData,
)
import logging
from enum import Enum


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

book_router = APIRouter()
changes_router = APIRouter()


class SortBy(str, Enum):
    # Ascending (no prefix)
    NO_OF_RATINGS_ASC = "no_of_ratings"
    NO_OF_REVIEWS_ASC = "no_of_reviews"
    PRICE_WITH_TAX_ASC = "price_with_tax"
    PRICE_WITHOUT_TAX_ASC = "price_without_tax"

    # Descending (with hyphen prefix)
    NO_OF_RATINGS_DESC = "-no_of_ratings"
    NO_OF_REVIEWS_DESC = "-no_of_reviews"
    PRICE_WITH_TAX_DESC = "-price_with_tax"
    PRICE_WITHOUT_TAX_DESC = "-price_without_tax"


def parse_sort_field(sort_by_param: SortBy):
    """Parse Django-style sort parameter from enum"""
    if sort_by_param.value.startswith("-"):
        # Descending order
        field = sort_by_param.value[1:]
        order = -1
    else:
        # Ascending order
        field = sort_by_param.value
        order = 1

    return field, order


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
    skip = (page - 1) * page_size

    query = {}
    if category:
        category_doc = await BookCategory.find_one(BookCategory.name == category)
        logger.info(f"category_doc: {category_doc}")
        if category_doc:
            query["category.$id"] = category_doc.id

    if rating:
        query["no_of_ratings"] = rating

    if min_price is not None:
        query["price_with_tax"] = {"$gte": min_price}

    if max_price is not None:
        if "price_with_tax" in query:
            query["price_with_tax"]["$lte"] = max_price
        else:
            query["price_with_tax"] = {"$lte": max_price}
    logger.info(f"Query: {query}")
    total_count = await Book.find(query).count()
    if sort_by:
        sort_field, sort_order = parse_sort_field(sort_by)
        logger.info(
            f"Sorting by: {sort_field} ({'desc' if sort_order == -1 else 'asc'})"
        )
        books = (
            await Book.find(query)
            .sort([(sort_field, sort_order)])
            .skip(skip)
            .limit(page_size)
            .to_list()
        )
    else:
        books = (
            await Book.find(query)
            .sort([("created_at", -1)])
            .skip(skip)
            .limit(page_size)
            .to_list()
        )

    total_pages = (total_count + page_size - 1) // page_size
    # Note: This is done to ensure raw_html is excluded.
    book_responses = []
    for book in books:
        await book.fetch_link(Book.category)
        book_data = BookPartialDetail(
            id=book.id,
            title=book.title,
            name=book.name,
            category=BookCategoryResponse(
                id=book.category.id,
                name=book.category.name,
                description=book.category.description,
            ),
            currency=book.currency,
            price_with_tax=book.price_with_tax,
            price_without_tax=book.price_without_tax,
            availability=book.availability,
            no_of_ratings=book.no_of_ratings,
            no_of_reviews=book.no_of_reviews,
            cover_image_url=book.cover_image_url,
        )
        book_responses.append(book_data)

    data = BooksListData(
        current_page=page,
        page_size=page_size,
        total_pages=total_pages,
        total_count=total_count,
        books=book_responses,
    )
    return SuccessResponse(
        status="success", message="Books retrieved successfully", data=data
    )


@book_router.get(
    "/{book_id}", response_model=BookDetailResponse, status_code=status.HTTP_200_OK
)
async def get_book_by_id(book_id: PydanticObjectId):
    """Get a specific book by ID."""
    book = await Book.get(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    await book.fetch_link(Book.category)
    book_detail = BookFullDetail(
        id=book.id,
        title=book.title,
        name=book.name,
        description=book.description,
        category=BookCategoryResponse(
            id=book.category.id,
            name=book.category.name,
            description=book.category.description,
        ),
        currency=book.currency,
        price_with_tax=book.price_with_tax,
        price_without_tax=book.price_without_tax,
        availability=book.availability,
        no_of_reviews=book.no_of_reviews,
        cover_image_url=book.cover_image_url,
        no_of_ratings=book.no_of_ratings,
        metadata=book.metadata,
        raw_html=book.raw_html,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )
    data = BookDetailData(book=book_detail)
    return SuccessResponse(
        status="success", message="Book retrieved successfully", data=data
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
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

    query = {"changed_at": {"$gte": cutoff_time}}
    if field:
        query["field_changed"] = field

    changes = (
        await ChangeLog.find(query).sort(-ChangeLog.changed_at).limit(limit).to_list()
    )
    change_responses = []
    for change in changes:
        if hasattr(change.book, "id"):
            book_id = change.book.id
        elif hasattr(change.book, "ref"):
            book_id = change.book.ref.id
        else:
            book_id = change.book

        change_data = ChangeLogData(
            id=change.id,
            book_id=book_id,
            field_changed=change.field_changed,
            old_value=change.old_value,
            new_value=change.new_value,
            changed_at=change.changed_at,
        )
        change_responses.append(change_data)

    data = ChangesListData(
        total=len(change_responses), period_hours=hours_back, changes=change_responses
    )

    return SuccessResponse(
        status="success", message="Changes retrieved successfully", data=data
    )
