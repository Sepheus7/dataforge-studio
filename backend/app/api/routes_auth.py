"""Authentication routes — token issuance for JWT auth flow."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.config import settings
from app.core.jwt import create_access_token

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post(
    "/auth/token",
    response_model=Token,
    summary="Exchange API key for a Bearer token",
    description=(
        "Submit your API key as the password (username can be any non-empty string). "
        "Returns a short-lived JWT for use in `Authorization: Bearer <token>` headers."
    ),
)
async def issue_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Exchange an API key for a JWT access token.

    This is the standard OAuth2 password flow adapted to use the API key as
    the credential.  When `ENABLE_JWT_AUTH=false` (the default) this endpoint
    still works but is not enforced by other routes.
    """
    if form_data.password != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.JWT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "JWT_SECRET_KEY is not configured on the server. "
                "Set it in your environment to enable token issuance."
            ),
        )

    token = create_access_token(subject=form_data.username or "api-client")
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
