"""API key authentication"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Optional

from app.core.config import settings

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header in your request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # In production, you would validate against a database or secret manager
    # For now, we validate against the configured API key
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


async def optional_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Optional API key verification for public endpoints.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The API key if provided and valid, None otherwise
    """
    if not api_key:
        return None

    try:
        return await verify_api_key(api_key)
    except HTTPException:
        return None
