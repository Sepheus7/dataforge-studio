"""JWT authentication utilities for DataForge Studio.

Usage:
  - Set ENABLE_JWT_AUTH=true and JWT_SECRET_KEY in your environment.
  - When enabled, clients must exchange credentials for a token at POST /v1/auth/token
    and include it as `Authorization: Bearer <token>` on subsequent requests.
  - The existing X-API-Key flow remains active for backwards compatibility and
    service-to-service calls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency: python-jose for JWT encoding/decoding
# ---------------------------------------------------------------------------
try:
    from jose import JWTError, jwt as _jwt

    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False
    logger.warning(
        "python-jose not installed. JWT authentication will be unavailable. "
        "Run: pip install python-jose[cryptography]"
    )

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token", auto_error=False)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject (e.g. username or client_id).
        expires_delta: Override the default expiry duration.

    Returns:
        Encoded JWT string.

    Raises:
        RuntimeError: If python-jose is not installed or JWT_SECRET_KEY is unset.
    """
    if not _JWT_AVAILABLE:
        raise RuntimeError(
            "python-jose is required for JWT auth. Install with: pip install python-jose[cryptography]"
        )
    if not settings.JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY must be set to use JWT authentication.")

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return _jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded token payload.

    Raises:
        HTTPException: 401 if the token is invalid or expired.
    """
    if not _JWT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not available (python-jose not installed).",
        )
    try:
        payload = _jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """FastAPI dependency that validates a Bearer token.

    Returns:
        The token subject (username / client ID) if valid, else None when
        JWT auth is disabled.

    Raises:
        HTTPException: 401 if JWT auth is enabled but token is missing/invalid.
    """
    if not settings.ENABLE_JWT_AUTH:
        # JWT auth disabled — callers fall back to API-key auth
        return None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required. Obtain one from POST /v1/auth/token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    return payload["sub"]
