import hashlib
import json
from typing import Any, Dict

from utilities.constants import BOOK_FIELDS_TO_TRACK


def generate_hash(data: dict) -> str:
    """Generates an MD5 hash of a dictionary's content."""
    # Ensure all the necessary fields to be included is present
    data = {key: data.get(key) for key in BOOK_FIELDS_TO_TRACK}
    # Ensure consistent order for hashing by sorting keys
    sorted_data = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(sorted_data.encode("utf-8")).hexdigest()


def detect_changes(old_book: dict, new_book: dict) -> Dict[str, Dict[str, Any]]:
    """
    Compare old and new book data and return what changed.
    """
    changes = {}

    for field in BOOK_FIELDS_TO_TRACK:
        old_value = old_book.get(field)
        new_value = new_book.get(field)

        if old_value != new_value:
            changes[field] = {
                "old": old_value,
                "new": new_value,
            }

    return changes
