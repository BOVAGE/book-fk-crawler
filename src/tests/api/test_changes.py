import pytest
from httpx import AsyncClient
from fastapi import status


class TestChangesEndpoints:
    """Test suite for changes API endpoints."""

    @pytest.mark.asyncio
    async def test_get_recent_changes(
        self, client: AsyncClient, api_headers, sample_changes
    ):
        """Test getting recent changes."""
        response = await client.get("/api/v1/changes", headers=api_headers)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Changes retrieved successfully"

        changes_data = data["data"]
        assert changes_data["total"] == 2
        assert changes_data["period_hours"] == 24
        assert len(changes_data["changes"]) == 2

    @pytest.mark.asyncio
    async def test_get_changes_with_limit(
        self, client: AsyncClient, api_headers, sample_changes
    ):
        """Test limiting number of changes returned."""
        response = await client.get("/api/v1/changes?limit=1", headers=api_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        assert len(data["changes"]) == 1

    @pytest.mark.asyncio
    async def test_get_changes_by_field(
        self, client: AsyncClient, api_headers, sample_changes
    ):
        """Test filtering changes by field."""
        response = await client.get(
            "/api/v1/changes?field=price_with_tax", headers=api_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Should only return price changes
        assert data["total"] == 1
        assert data["changes"][0]["field_changed"] == "price_with_tax"

    @pytest.mark.asyncio
    async def test_get_changes_different_time_window(
        self, client: AsyncClient, api_headers, sample_changes
    ):
        """Test different time windows."""
        response = await client.get("/api/v1/changes?hours_back=1", headers=api_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        assert data["period_hours"] == 1
        # Should still return our test changes since they're recent

    @pytest.mark.parametrize(
        "limit,hours_back,expected_status",
        [
            (0, 24, 422),  # limit must be >= 1
            (101, 24, 422),  # limit must be <= 100
            (50, 0, 422),  # hours_back must be >= 1
            (50, 169, 422),  # hours_back must be <= 168
        ],
    )
    @pytest.mark.asyncio
    async def test_get_changes_validation_errors(
        self, client: AsyncClient, api_headers, limit, hours_back, expected_status
    ):
        """Test validation errors for changes parameters."""
        response = await client.get(
            f"/api/v1/changes?limit={limit}&hours_back={hours_back}",
            headers=api_headers,
        )
        assert response.status_code == expected_status
