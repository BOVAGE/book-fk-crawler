import pytest
from utilities.utils import generate_hash, detect_changes


class TestUtilities:
    """Test utility functions."""

    def test_generate_hash_same_data(self):
        """Test that same data generates same hash."""
        data1 = {
            "book_id": "692a811d9495cac0ecc2d907",
            "title": "rat-queens-vol-3-demons-rat-queens-collected-editions-11-15_921",
            "name": "Rat Queens, Vol. 3: Demons (Rat Queens (Collected Editions) #11-15)",
            "category": "Sequential Art",
            "currency": "£",
            "price_with_tax": 50.4,
            "price_without_tax": 50.4,
            "created_at": "2025-11-29T05:10:51.152000",
        }
        data2 = {
            "book_id": "692a811d9495cac0ecc2d907",
            "title": "rat-queens-vol-3-demons-rat-queens-collected-editions-11-15_921",
            "name": "Rat Queens, Vol. 3: Demons (Rat Queens (Collected Editions) #11-15)",
            "category": "Sequential Art",
            "currency": "£",
            "price_with_tax": 50.4,
            "price_without_tax": 50.4,
            "created_at": "2025-11-29T05:10:51.152000",
        }

        hash1 = generate_hash(data1)
        hash2 = generate_hash(data2)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) > 10

    def test_generate_hash_different_data(self):
        """Test that different data generates different hashes."""
        data1 = {
            "book_id": "692a811d9495cac0ecc2d907",
            "title": "rat-queens-vol-3-demons-rat-queens-collected-editions-11-15_921",
            "name": "Rat Queens, Vol. 3: Demons (Rat Queens (Collected Editions) #11-15)",
            "category": "Sequential Art",
            "currency": "£",
            "price_with_tax": 50.4,
            "price_without_tax": 50.4,
            "no_of_reviews": 2,
            "no_of_rating": 4,
            "created_at": "2025-11-29T05:10:51.152000",
        }
        data2 = {
            "book_id": "692a811d9495cac0ecc2d907",
            "title": "elephant-queens-vol-3-demons-elephant-queens-collected-editions-11-15_921",
            "name": "elephant Queens, Vol. 3: Demons (elephant Queens (Collected Editions) #11-15)",
            "category": "Sequential Art",
            "currency": "£",
            "price_with_tax": 52.4,
            "price_without_tax": 52.4,
            "no_of_reviews": 2,
            "no_of_rating": 4,
            "created_at": "2025-11-29T05:10:51.152000",
        }

        hash1 = generate_hash(data1)
        hash2 = generate_hash(data2)

        assert hash1 != hash2

    def test_detect_changes_no_changes(self):
        """Test detecting no changes between identical data."""
        old_data = {
            "title": "book-1",
            "price_with_tax": 19.99,
            "availability": "In stock",
            "category": "Fiction",
        }
        new_data = {
            "title": "book-1",
            "price_with_tax": 19.99,
            "availability": "In stock",
            "category": "Fiction",
        }

        changes = detect_changes(old_data, new_data)
        assert changes == {}

    def test_detect_changes_price_change(self):
        """Test detecting price changes."""
        old_data = {
            "title": "book-1",
            "price_with_tax": 19.99,
            "availability": "In stock",
        }
        new_data = {
            "title": "book-1",
            "price_with_tax": 24.99,  # Changed
            "availability": "In stock",
        }

        changes = detect_changes(old_data, new_data)

        assert "price_with_tax" in changes
        assert changes["price_with_tax"]["old"] == 19.99
        assert changes["price_with_tax"]["new"] == 24.99

    def test_detect_changes_multiple_changes(self):
        """Test detecting multiple changes."""
        old_data = {
            "price_with_tax": 19.99,
            "availability": "In stock (10 available)",
            "no_of_reviews": 5,
        }
        new_data = {
            "price_with_tax": 24.99,  # Changed
            "availability": "In stock (3 available)",  # Changed
            "no_of_reviews": 5,  # Unchanged
        }

        changes = detect_changes(old_data, new_data)

        assert len(changes) == 2
        assert "price_with_tax" in changes
        assert "availability" in changes
        assert "no_of_reviews" not in changes
