"""Rate limiting for DataForge Studio API.

Uses slowapi (a Starlette/FastAPI wrapper around limits).

Configuration (via environment variables):
  RATE_LIMIT_ENABLED  - Set to "true" to enable (default: false in dev, true in prod)
  RATE_LIMIT_DEFAULT  - Default limit string, e.g. "60/minute" (default: "60/minute")
  RATE_LIMIT_GENERATION - Stricter limit for generation endpoints (default: "10/minute")

The limiter uses the client IP address as the key. In production behind a load
balancer, ensure X-Forwarded-For is forwarded and trusted.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional slowapi import
# ---------------------------------------------------------------------------
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    _SLOWAPI_AVAILABLE = True
except ImportError:
    _SLOWAPI_AVAILABLE = False
    logger.warning(
        "slowapi not installed. Rate limiting will be disabled. "
        "Run: pip install slowapi"
    )


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def create_limiter(default_limit: str = "60/minute") -> Optional[object]:
    """Create and return a configured Limiter instance, or None if slowapi is unavailable."""
    if not _SLOWAPI_AVAILABLE:
        return None

    limiter = Limiter(key_func=_get_client_ip, default_limits=[default_limit])
    return limiter


def get_rate_limit_exceeded_handler():
    """Return the 429 handler for slowapi, or None if unavailable."""
    if not _SLOWAPI_AVAILABLE:
        return None
    return _rate_limit_exceeded_handler


def get_rate_limit_exceeded_error():
    """Return the RateLimitExceeded exception class, or None if unavailable."""
    if not _SLOWAPI_AVAILABLE:
        return None
    return RateLimitExceeded
