"""This file contains the authentication utilities for the application."""

import re
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Optional, Dict, Any

from jose import (
    JWTError,
    jwt,
)

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil
from app.schemas.auth import Token
from app.utils.sanitization import sanitize_string


def create_access_token(
    thread_id: str,
    user_data: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> Token:
    """Create a new access token for a user.

    Args:
        thread_id: The unique thread ID for the conversation (kept for backward compatibility).
        user_data: Optional dictionary containing user information (id, email, oid, status, etc.)
        expires_delta: Optional expiration time delta.

    Returns:
        Token: The generated access token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(
            UTC) + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": thread_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        # Add unique token identifier
        "jti": sanitize_string(f"{thread_id}-{datetime.now(UTC).timestamp()}"),
    }

    # Add user data to token if provided
    if user_data:
        to_encode["user"] = {
            "id": str(user_data.get("id", "")),
            "email": user_data.get("email", ""),
            "oid": user_data.get("oid", 0),
            "status": user_data.get("status", 1),
        }

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    TerraLogUtil.info("token_created", thread_id=thread_id,
                      user_id=user_data.get("id") if user_data else None,
                      expires_at=expire.isoformat())

    return Token(access_token=encoded_jwt, expires_at=expire)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return the user data.

    Args:
        token: The JWT token to verify.

    Returns:
        Optional[Dict[str, Any]]: The user data if token is valid, None otherwise.
            Contains: id, email, oid, status

    Raises:
        ValueError: If the token format is invalid
    """
    if not token or not isinstance(token, str):
        TerraLogUtil.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")

    # Basic format validation before attempting decode
    # JWT tokens consist of 3 base64url-encoded segments separated by dots
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        TerraLogUtil.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY,
                             algorithms=[settings.JWT_ALGORITHM])
        user_data: Dict[str, Any] = payload.get("user")
        if user_data is None:
            TerraLogUtil.warning("token_missing_user_data")
            return None

        TerraLogUtil.info("token_verified", user_id=user_data.get("id"))
        return user_data

    except JWTError as e:
        TerraLogUtil.error("token_verification_failed",
                           error=str(e), exc_info=True)
        return None
