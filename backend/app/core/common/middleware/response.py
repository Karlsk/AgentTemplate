"""Middleware for wrapping API responses in a unified format."""

import json
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil


class ResponseMiddleware(BaseHTTPMiddleware):
    """Middleware for wrapping API responses in a unified format.

    Wraps successful JSON responses in {code: 0, data: ..., msg: null} format.
    Skips wrapping for specific paths like docs, openapi, and direct paths.
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process response and wrap in unified format if needed.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response, possibly wrapped in unified format
        """
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception from downstream middleware/routes
            import traceback
            TerraLogUtil.error(
                "response_middleware_caught_exception",
                error=str(e),
                error_type=type(e).__name__,
                path=request.url.path,
                method=request.method,
                traceback=traceback.format_exc(),
                exc_info=True,
            )
            # Re-raise to let FastAPI's exception handlers deal with it
            raise

        # Paths that should not be wrapped
        direct_paths = [
            f"{settings.API_V1_STR}/mcp/mcp_question",
            f"{settings.API_V1_STR}/mcp/mcp_assistant",
            "/openapi.json",
            "/docs",
            "/redoc",
        ]

        route = request.scope.get("route")
        path_pattern = "" if not route else route.path_format

        # Skip wrapping for specific conditions
        if isinstance(response, JSONResponse) and request.url.path in direct_paths:
            return response

        if request.url.path == "/openapi.json" or path_pattern in direct_paths:
            return response

        # Log non-200 responses for debugging
        if response.status_code != 200:
            TerraLogUtil.error(
                "server_error_response",
                path=request.url.path,
                status_code=response.status_code,
            )
            return response

        if response.headers.get("content-type") != "application/json":
            return response

        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            raw_data = json.loads(body.decode())

            # Check if already wrapped
            if (
                isinstance(raw_data, dict)
                and all(k in raw_data for k in ["code", "data", "msg"])
            ):
                return JSONResponse(
                    content=raw_data,
                    status_code=response.status_code,
                    headers={
                        k: v
                        for k, v in response.headers.items()
                        if k.lower() not in ("content-length", "content-type")
                    },
                )

            # Wrap the response
            wrapped_data = {"code": 0, "data": raw_data, "msg": None}

            return JSONResponse(
                content=wrapped_data,
                status_code=response.status_code,
                headers={
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "content-type")
                },
            )

        except Exception as e:
            TerraLogUtil.error(
                "response_processing_error",
                error=str(e),
                path=request.url.path,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"code": 500, "data": None, "msg": str(e)},
                headers={
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "content-type")
                },
            )
