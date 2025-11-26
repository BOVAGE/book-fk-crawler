from bs4 import BeautifulSoup
from urllib.parse import urljoin
from decimal import Decimal
from utilities.constants import BASE_URL
from typing import Dict, Any



def parse_book_list(html: str) -> list[str]:
    """Extract URLs of books on the page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for article in soup.select(".product_pod h3 a"):
        book_rel_url = article.get("href")
        links.append(urljoin(BASE_URL + "catalogue/", book_rel_url))
    return links


def parse_book_details(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    # extract unique title from the url
    # url format: "https://books.toscrape.com/catalogue/soumission_998/index.html"
    # the unique title comes before "/index.html", right after "catalogue"
    title = url.split("/")[-2]  # Extract the unique title from the URL
    name = soup.find("h1").get_text(strip=True)

    # Description (sometimes missing)
    desc_tag = soup.select_one("#product_description + p")
    description = desc_tag.text.strip() if desc_tag else None

    # Category
    category = soup.select("ul.breadcrumb li a")[-1].text.strip()

    # Price info
    table = soup.select_one("table.table.table-striped")
    rows = {row.th.text.strip(): row.td.text.strip() for row in table.find_all("tr")}

    currency_1 = rows["Price (incl. tax)"][0]
    currency_2 = rows["Price (excl. tax)"][0]
    assert currency_1 == currency_2, "Different currencies found!"
    currency = currency_1
    price_incl = Decimal(rows["Price (incl. tax)"][1:])
    price_excl = Decimal(rows["Price (excl. tax)"][1:])

    # Availability
    availability = rows[
        "Availability"
    ]  # int(''.join(filter(str.isdigit, rows["Availability"])))

    # Rating
    rating_str = soup.select_one(".star-rating")["class"][1]
    rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    rating = rating_map.get(rating_str, 0)

    # Number of reviews
    reviews = int(rows["Number of reviews"])

    # Image
    img_rel = soup.select_one(".item.active img")["src"]
    image_url = urljoin(BASE_URL, img_rel)

    return {
        "title": title,
        "name": name,
        "description": description,
        "category": category,
        "currency": currency,
        "price_with_tax": price_incl,
        "price_without_tax": price_excl,
        "availability": availability,
        "no_of_reviews": reviews,
        "no_of_ratings": rating,
        "image_url": image_url,
        "source_url": url,
        "raw_html": html,
    }
