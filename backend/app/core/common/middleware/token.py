"""Token authentication middleware for extracting user and session info."""

from typing import Callable, Optional, Dict, Any

from fastapi import Request, status
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil
from app.services.auth import AuthService
from app.models.session import SessionModel
from app.models.user import UserModel


class TokenMiddleware(BaseHTTPMiddleware):
    """Middleware for extracting user and session info from JWT token.

    This middleware extracts the JWT token from the Authorization header,
    validates it, and sets the user and session information in request.state.

    Attributes:
        request.state.user: The authenticated UserModel instance (if valid token)
        request.state.session: The authenticated SessionModel instance (if valid token)
        request.state.user_id: The user ID extracted from token
        request.state.session_id: The session ID extracted from token
        request.state.user_info: The user info dict from token (id, email, oid, status)
    """

    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract and validate token, set user/session info in request.state.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the application
        """
        # Initialize state attributes
        request.state.user = None
        request.state.user_id = None
        request.state.session_id = None

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            try:
                # Decode token to get user info
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                user_id = payload.get("sub")
                user_info: Dict[str, Any] = payload.get("user")

                if user_id:
                    request.state.user_id = int(user_id)

                if user_info:
                    # Store user info from token
                    request.state.user = user_info

                if user_id:
                    # Try to get session_id from header first
                    session_id = request.headers.get("X-Session-Id")

                    request.state.session_id = session_id

            except JWTError as e:
                # Token is invalid - don't fail here, let endpoints handle auth
                TerraLogUtil.warning(
                    "token_middleware_jwt_decode_failed",
                    error=str(e),
                    path=request.url.path
                )
            except Exception as e:
                # Other errors - don't fail the request but log them
                TerraLogUtil.error(
                    "token_middleware_unexpected_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    path=request.url.path,
                    exc_info=True
                )

        # Process the request
        response = await call_next(request)
        return response
