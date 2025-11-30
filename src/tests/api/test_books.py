import pytest
from fastapi import status
from httpx import AsyncClient


class TestBooksEndpoints:
    """Test suite for books API endpoints."""

    @pytest.mark.asyncio
    async def test_get_books_without_filters(
        self, client: AsyncClient, api_headers, sample_books
    ):
        """Test getting books without any filters."""
        response = await client.get("/api/v1/books", headers=api_headers)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Books retrieved successfully"
        assert "data" in data

        books_data = data["data"]
        assert books_data["current_page"] == 1
        assert books_data["page_size"] == 10
        assert books_data["total_count"] == 3  # We created 3 sample books
        assert len(books_data["books"]) == 3

    @pytest.mark.asyncio
    async def test_get_books_pagination(
        self, client: AsyncClient, api_headers, sample_books
    ):
        """Test books pagination."""
        # Test first page with page_size=2
        response = await client.get(
            "/api/v1/books?page=1&page_size=2", headers=api_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["current_page"] == 1
        assert data["page_size"] == 2
        assert data["total_count"] == 3
        assert data["total_pages"] == 2  # 3 books / 2 per page = 2 pages
        assert len(data["books"]) == 2

        # Test second page
        response = await client.get(
            "/api/v1/books?page=2&page_size=2", headers=api_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["current_page"] == 2
        assert len(data["books"]) == 1  # Only 1 book left

    @pytest.mark.asyncio
    async def test_get_books_filter_by_category(
        self, client: AsyncClient, api_headers, sample_books
    ):
        """Test filtering books by category."""
        response = await client.get(
            "/api/v1/books?category=Fiction", headers=api_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Should return 2 fiction books
        assert data["total_count"] == 2
        assert len(data["books"]) == 2

        # Verify all returned books are Fiction
        for book in data["books"]:
            assert book["category"]["name"] == "Fiction"

    @pytest.mark.asyncio
    async def test_get_books_filter_by_price_range(
        self, client: AsyncClient, api_headers, sample_books
    ):
        """Test filtering books by price range."""
        # Test min_price filter
        response = await client.get("/api/v1/books?min_price=20", headers=api_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Should return 2 books (Science book: 25.50, Expensive book: 99.99)
        assert data["total_count"] == 2

        # Verify all books meet min price
        for book in data["books"]:
            assert float(book["price_with_tax"]) >= 20.0

    @pytest.mark.asyncio
    async def test_get_books_sorting(
        self, client: AsyncClient, api_headers, sample_books
    ):
        """Test sorting books."""
        # Test sorting by price ascending
        response = await client.get(
            "/api/v1/books?sort_by=price_with_tax", headers=api_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        books = data["books"]
        assert len(books) == 3

        # Verify ascending price order
        prices = [float(book["price_with_tax"]) for book in books]
        assert prices == sorted(prices)

        # Test sorting by price descending
        response = await client.get(
            "/api/v1/books?sort_by=-price_with_tax", headers=api_headers
        )

        data = response.json()["data"]
        books = data["books"]

        # Verify descending price order
        prices = [float(book["price_with_tax"]) for book in books]
        assert prices == sorted(prices, reverse=True)

    @pytest.mark.asyncio
    async def test_get_books_invalid_category(self, client: AsyncClient, api_headers):
        """Test filtering with non-existent category."""
        response = await client.get(
            "/api/v1/books?category=NonExistent", headers=api_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Should return empty results
        assert data["total_count"] == 0
        assert len(data["books"]) == 0

    @pytest.mark.asyncio
    async def test_get_book_by_id(self, client: AsyncClient, api_headers, sample_books):
        """Test getting a specific book by ID."""
        book_id = str(sample_books[0].id)

        response = await client.get(f"/api/v1/books/{book_id}", headers=api_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        assert data["message"] == "Book retrieved successfully"

        book = data["data"]["book"]
        assert book["id"] == book_id
        assert book["title"] == "test-book-1"
        assert book["name"] == "The Great Test"
        assert "raw_html" in book  # Full detail includes raw_html
        assert "metadata" in book

    @pytest.mark.asyncio
    async def test_get_book_by_invalid_id(self, client: AsyncClient, api_headers):
        """Test getting book with non-existent ID."""
        invalid_id = (
            "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
        )

        response = await client.get(f"/api/v1/books/{invalid_id}", headers=api_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_get_books_without_api_key(self, client: AsyncClient):
        """Test that API key is required."""
        response = await client.get("/api/v1/books")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_books_invalid_api_key(self, client: AsyncClient):
        """Test with invalid API key."""
        headers = {"x-api-key": "invalid-key"}
        response = await client.get("/api/v1/books", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "page,page_size,expected_status",
        [
            (0, 10, 422),  # page must be >= 1
            (1, 0, 422),  # page_size must be >= 1
            (1, 101, 422),  # page_size must be <= 100
            (-1, 10, 422),  # negative page
            (1, -5, 422),  # negative page_size
        ],
    )
    @pytest.mark.asyncio
    async def test_get_books_validation_errors(
        self, client: AsyncClient, api_headers, page, page_size, expected_status
    ):
        """Test validation errors for pagination parameters."""
        response = await client.get(
            f"/api/v1/books?page={page}&page_size={page_size}", headers=api_headers
        )
        assert response.status_code == expected_status
