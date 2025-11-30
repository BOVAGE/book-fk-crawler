import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FKCrawler/1.0)"}


def should_retry(exception):
    """Only retry if it's not a 404 error"""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code != 404
    return True


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception(should_retry),
)
async def fetch_html(url: str) -> str:
    """
    Fetch HTML content from a URL.
    Raises httpx.HTTPStatusError on non-200 responses.
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


if __name__ == "__main__":
    import asyncio

    from tenacity import RetryError

    try:
        asyncio.run(fetch_html("https://books.toscrape.com/catalogue/page-70.html"))
    except Exception as e:
        if isinstance(e, RetryError):
            last_attempt = e.last_attempt

            if last_attempt.failed:
                original_exception = last_attempt.exception()
                if original_exception.response.status_code == 404:
                    print("Page not found (404).")
        else:
            print(f"Failed to fetch page: {e}", e.__class__)
