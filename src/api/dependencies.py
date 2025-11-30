from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from config import settings

api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == settings.SECRET_API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API Key",
    )


async def get_api_key_from_header(request: Request):
    user_id = request.headers.get("x-api-key")
    return user_id
