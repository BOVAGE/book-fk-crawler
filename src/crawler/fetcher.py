import httpx
from tenacity import retry, wait_exponential, stop_after_attempt

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FKCrawler/1.0)"}


@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
