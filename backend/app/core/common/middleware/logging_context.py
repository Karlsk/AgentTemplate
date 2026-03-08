"""Middleware for adding user_id and session_id to logging context."""

import time
from typing import Callable, Optional

from fastapi import Request
from jose import (
    JWTError,
    jwt,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.common.config import settings
from app.core.common.logging import (
    bind_context,
    clear_context,
    TerraLogUtil,
)


# Paths to skip from detailed request logging (health checks, metrics, etc.)
SKIP_LOG_PATHS: set[str] = {
    "/health",
    "/metrics",
    "/",
}


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Middleware for adding user_id, session_id to logging context and logging HTTP request details."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract user_id and session_id from authenticated requests and log HTTP details.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the application
        """
        start_time = time.perf_counter()

        try:
            # Clear any existing context from previous requests
            clear_context()

            # Extract token from Authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

                try:
                    # Decode token to get session_id (stored in "sub" claim)
                    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[
                                         settings.JWT_ALGORITHM])
                    session_id = payload.get("sub")

                    if session_id:
                        # Bind session_id to logging context
                        bind_context(session_id=session_id)

                except JWTError:
                    # Token is invalid, but don't fail the request - let the auth dependency handle it
                    pass

            # Process the request
            response = await call_next(request)

            # After request processing, check if user info was added to request state
            if hasattr(request.state, "user_id"):
                bind_context(user_id=request.state.user_id)

            # Log HTTP request details (skip health checks and metrics)
            if request.url.path not in SKIP_LOG_PATHS:
                process_time = time.perf_counter() - start_time
                await self._log_request(request, response, process_time)

            return response

        finally:
            # Always clear context after request is complete to avoid leaking to other requests
            clear_context()

    async def _log_request(self, request: Request, response: Response, process_time: float) -> None:
        """Log detailed HTTP request information.

        Args:
            request: The incoming request
            response: The response from the application
            process_time: Time taken to process the request in seconds
        """
        # Get client IP
        client_host: Optional[str] = None
        if request.client:
            client_host = request.client.host
        # Check for X-Forwarded-For header (proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()

        # Get query params
        query_params = dict(
            request.query_params) if request.query_params else None

        # Build log data
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "client_host": client_host,
        }

        # Add query params if present
        if query_params:
            log_data["query_params"] = query_params

        # Add content type if present
        content_type = request.headers.get("content-type")
        if content_type:
            log_data["content_type"] = content_type

        # Add content length if present
        content_length = request.headers.get("content-length")
        if content_length:
            log_data["request_length"] = content_length

        # Add response content length if present
        response_length = response.headers.get("content-length")
        if response_length:
            log_data["response_length"] = response_length

        # Add user agent if present
        user_agent = request.headers.get("user-agent")
        if user_agent:
            # Truncate long user agents
            log_data["user_agent"] = user_agent[:200]

        # Log based on status code level
        if response.status_code >= 500:
            TerraLogUtil.error("http_request_server_error", **log_data)
        elif response.status_code >= 400:
            TerraLogUtil.warning("http_request_client_error", **log_data)
        else:
            TerraLogUtil.info("http_request_completed", **log_data)
