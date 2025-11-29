from typing import Any, List, Optional, Dict, Generic, TypeVar
from pydantic import BaseModel
from beanie import PydanticObjectId
from decimal import Decimal
from datetime import datetime
from crawler.models import Metadata

T = TypeVar("T")


# JSend standard response models
class SuccessResponse(BaseModel, Generic[T]):
    """Schema for successful responses"""

    status: str = "success"
    message: str
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Schema for error responses"""

    status: str = "error"
    message: str = "An error occurred"
    error: Dict[str, List[str]]


# Book response schemas
class BookCategoryResponse(BaseModel):
    """Schema for book category info"""

    id: PydanticObjectId
    name: str
    description: Optional[str] = None


class BookFullDetail(BaseModel):
    """Detailed book info for single book view"""

    id: PydanticObjectId
    title: str
    name: str
    description: Optional[str] = None
    category: BookCategoryResponse
    currency: str
    price_with_tax: Decimal
    price_without_tax: Decimal
    availability: str
    no_of_reviews: int
    cover_image_url: Optional[str] = None
    no_of_ratings: int
    metadata: Metadata
    raw_html: Optional[str]
    created_at: datetime
    updated_at: datetime


class BookPartialDetail(BaseModel):
    """Simplified book info for list view"""

    id: PydanticObjectId
    title: str
    name: str
    category: BookCategoryResponse
    currency: str
    price_with_tax: Decimal
    price_without_tax: Decimal
    availability: str
    no_of_ratings: int
    no_of_reviews: int
    cover_image_url: Optional[str] = None


class BooksListData(BaseModel):
    """Data container for books list with pagination at top level"""

    current_page: int
    page_size: int
    total_pages: int
    total_count: int
    books: List[BookPartialDetail]


class BookDetailData(BaseModel):
    """Data container for single book detail"""

    book: BookFullDetail


# Change log schemas
class ChangeLogData(BaseModel):
    """Schema for a single change log entry"""

    id: PydanticObjectId
    book_id: PydanticObjectId
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime


class ChangesListData(BaseModel):
    """Data container for changes list"""

    total: int
    period_hours: int
    changes: List[ChangeLogData]


BooksListResponse = SuccessResponse[BooksListData]
BookDetailResponse = SuccessResponse[BookDetailData]
ChangesListResponse = SuccessResponse[ChangesListData]
