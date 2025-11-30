from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId

from api.exceptions import BookNotFoundError
from api.schemas import (
    BookCategoryResponse,
    BookDetailData,
    BookFullDetail,
    BookPartialDetail,
    BooksListData,
    ChangeLogData,
    ChangesListData,
    SortBy,
)
from src.models import Book, BookCategory, ChangeLog


class BookService:
    """Service for book-related business logic"""

    async def get_books_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        category: Optional[str] = None,
        rating: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: Optional[SortBy] = None,
    ) -> BooksListData:
        """Get paginated books with filtering and sorting"""

        # Build query
        query = await self._build_books_query(
            category=category, rating=rating, min_price=min_price, max_price=max_price
        )

        # Calculate pagination
        skip = (page - 1) * page_size

        total_count = await Book.find(query).count()
        total_pages = (total_count + page_size - 1) // page_size

        # Build and execute query with sorting
        books_query = Book.find(query)

        if sort_by:
            sort_field, sort_order = self._parse_sort_field(sort_by)
            books_query = books_query.sort([(sort_field, sort_order)])
        else:
            books_query = books_query.sort([("created_at", -1)])

        books = await books_query.skip(skip).limit(page_size).to_list()

        # Transform to response format
        book_responses = []
        for book in books:
            await book.fetch_link(Book.category)
            book_data = await self._transform_book_partial(book)
            book_responses.append(book_data)

        return BooksListData(
            current_page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
            books=book_responses,
        )

    async def get_book_by_id(self, book_id: PydanticObjectId) -> BookDetailData:
        """Get single book with full details"""

        book = await Book.get(book_id)
        if not book:
            raise BookNotFoundError(f"Book with ID {book_id} not found")

        await book.fetch_link(Book.category)
        book_detail = await self._transform_book_full(book)

        return BookDetailData(book=book_detail)

    async def _build_books_query(
        self,
        category: Optional[str] = None,
        rating: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Build MongoDB query for books filtering"""
        query = {}

        if category:
            category_doc = await BookCategory.find_one(BookCategory.name == category)
            if category_doc:
                query["category.$id"] = category_doc.id
            else:
                # Return query that matches nothing if category doesn't exist
                query["category.$id"] = PydanticObjectId()

        if rating:
            query["no_of_ratings"] = rating

        # Handle price range
        price_conditions = {}
        if min_price is not None:
            price_conditions["$gte"] = min_price
        if max_price is not None:
            price_conditions["$lte"] = max_price

        if price_conditions:
            query["price_with_tax"] = price_conditions

        return query

    def _parse_sort_field(self, sort_by: SortBy) -> Tuple[str, int]:
        """Parse Django-style sort parameter"""
        if sort_by.value.startswith("-"):
            # Descending order
            field = sort_by.value[1:]
            order = -1
        else:
            # Ascending order
            field = sort_by.value
            order = 1

        return field, order

    async def _transform_book_partial(self, book: Book) -> BookPartialDetail:
        """Transform Book model to partial detail response"""
        return BookPartialDetail(
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

    async def _transform_book_full(self, book: Book) -> BookFullDetail:
        """Transform Book model to full detail response"""
        return BookFullDetail(
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


class ChangesService:
    """Service for change tracking business logic"""

    async def get_recent_changes(
        self,
        limit: int = 50,
        hours_back: int = 24,
        field: Optional[str] = None,
    ) -> ChangesListData:
        """Get recent changes with filtering"""

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Build query
        query = {"changed_at": {"$gte": cutoff_time}}
        if field:
            query["field_changed"] = field

        # Execute query
        changes = await (
            ChangeLog.find(query).sort(-ChangeLog.changed_at).limit(limit).to_list()
        )

        # Transform to response format
        change_responses = []
        for change in changes:
            change_data = await self._transform_change_log(change)
            change_responses.append(change_data)

        return ChangesListData(
            total=len(change_responses),
            period_hours=hours_back,
            changes=change_responses,
        )

    async def _transform_change_log(self, change: ChangeLog) -> ChangeLogData:
        """Transform ChangeLog model to response format"""

        # Handle different ways book ID might be stored
        if hasattr(change.book, "id"):
            book_id = change.book.id
        elif hasattr(change.book, "ref"):
            book_id = change.book.ref.id
        else:
            book_id = change.book

        return ChangeLogData(
            id=change.id,
            book_id=book_id,
            field_changed=change.field_changed,
            old_value=change.old_value,
            new_value=change.new_value,
            changed_at=change.changed_at,
        )
