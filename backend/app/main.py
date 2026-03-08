"""This file contains the main application entry point."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from langfuse import Langfuse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from alembic import command
from alembic.config import Config

from app.api.v1.api import api_router
from app.core.common.cache import init_cache
from app.core.common.config import settings
from app.core.common.limiter import limiter
from app.core.common.logging import TerraLogUtil
from app.core.common.metrics import setup_metrics
from app.core.common.middleware import (
    LoggingContextMiddleware,
    MetricsMiddleware,
    ResponseMiddleware,
    TokenMiddleware
)
from app.core.common.deps import SessionDep
from sqlmodel import Session, select

# Load environment variables
load_dotenv()

# Initialize Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)


def run_migrations():
    import logging
    # Save current root logger level before alembic modifies it
    root_logger = logging.getLogger()
    saved_level = root_logger.level

    # Get the project root directory (parent of app directory)
    project_root = Path(__file__).parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    command.upgrade(alembic_cfg, "head")

    # Restore root logger level after alembic potentially changed it
    root_logger.setLevel(saved_level)
    TerraLogUtil.info("database_migrations_run")


def init_default_data():
    """Initialize default admin user and workspace if not exist."""
    from app.core.common.db import engine
    from app.models.user import UserModel, WorkSpaceModel
    from sqlmodel import Session, select

    with Session(engine) as session:
        # Check if default workspace exists
        result = session.execute(
            select(WorkSpaceModel).where(
                WorkSpaceModel.name == "Default Workspace")
        )
        workspace = result.scalar_one_or_none()

        if not workspace:
            # Create default workspace
            workspace = WorkSpaceModel(
                name="Default Workspace",
                description="Default system workspace",
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
            TerraLogUtil.info("default_workspace_created",
                              workspace_id=workspace.id)
        else:
            TerraLogUtil.info("default_workspace_exists",
                              workspace_id=workspace.id)

        # Check if admin user exists
        result = session.execute(
            select(UserModel).where(UserModel.email == "dms@admin.com")
        )
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            # Create default admin user
            admin_user = UserModel(
                email="dms@admin.com",
                hashed_password=UserModel.hash_password(settings.DEFAULT_PWD),
                oid=workspace.id,
                status=1,
            )
            session.add(admin_user)
            session.commit()
            TerraLogUtil.info("default_admin_user_created",
                              email="dms@admin.com")
        else:
            TerraLogUtil.info("default_admin_user_exists",
                              email="dms@admin.com")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    TerraLogUtil.info(
        "application_startup",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_STR,
    )
    run_migrations()
    init_default_data()
    init_cache()
    TerraLogUtil.info("application_startup_complete")
    yield
    TerraLogUtil.info("application_shutdown")


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags and len(route.tags) > 0 else ""
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    # openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set up Prometheus metrics
setup_metrics(app)

# Add logging context middleware (must be added before other middleware to capture context)
app.add_middleware(LoggingContextMiddleware)

# Add custom metrics middleware
app.add_middleware(MetricsMiddleware)

# Set up rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Add validation exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from request data.

    Args:
        request: The request that caused the validation error
        exc: The validation error

    Returns:
        JSONResponse: A formatted error response
    """
    # Log the validation error
    TerraLogUtil.error(
        "validation_error",
        client_host=request.client.host if request.client else "unknown",
        path=request.url.path,
        errors=str(exc.errors()),
    )

    # Format the errors to be more user-friendly
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join([str(loc_part)
                          for loc_part in error["loc"] if loc_part != "body"])
        formatted_errors.append({"field": loc, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": formatted_errors},
    )


# Add global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The unhandled exception

    Returns:
        JSONResponse: A formatted error response
    """
    import traceback

    # Get full traceback as string
    tb_str = traceback.format_exc()

    # Log the exception with full traceback
    TerraLogUtil.error(
        "unhandled_exception",
        client_host=request.client.host if request.client else "unknown",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=tb_str,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
        },
    )


# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins if settings.all_cors_origins else [
        "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TokenMiddleware)
app.add_middleware(ResponseMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def root(request: Request):
    """Root endpoint returning basic API information."""
    TerraLogUtil.info("root_endpoint_called")
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT.value,
        "swagger_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["health"][0])
async def health_check(
    request: Request,
    session: SessionDep
) -> Dict[str, Any]:
    """Health check endpoint with environment-specific information.

    Returns:
        Dict[str, Any]: Health status information
    """
    TerraLogUtil.info("health_check_called")
    health_flag = True
    # Check database connectivity
    try:
        session.exec(select(1)).first()
        db_healthy = True
    except Exception as e:
        TerraLogUtil.error("database_health_check_failed", error=str(e))
        db_healthy = False
        health_flag = False

    TerraLogUtil.info("database_health_check", db_healthy=db_healthy)

    response = {
        "status": "healthy" if health_flag else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {"api": "healthy", "database": "healthy" if db_healthy else "unhealthy"},
        "timestamp": datetime.now().isoformat(),
    }

    # If DB is unhealthy, set the appropriate status code
    status_code = status.HTTP_200_OK if health_flag else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010)
