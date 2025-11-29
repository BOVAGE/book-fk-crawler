from typing import List

BASE_URL: str = "https://books.toscrape.com/"
BASE_PAGE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
BOOK_FIELDS_TO_TRACK: List[str] = [
    "currency",
    "price_with_tax",
    "price_without_tax",
    "availability",
    "no_of_reviews",
    "no_of_ratings",
]
SIGNIFICANT_CHANGE_THRESHOLD = 10
