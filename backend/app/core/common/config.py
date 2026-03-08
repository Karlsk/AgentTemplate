"""Application configuration management.

This module handles environment-specific configuration loading, parsing, and management
for the application. It includes environment detection, .env file loading, and
configuration value parsing.
"""

import os
import secrets
from textwrap import TextWrapper
import urllib.parse
from enum import Enum
from pathlib import Path
from typing import (
    Annotated,
    Any,
    ClassVar,
    List,
    Optional,
)

from dotenv import load_dotenv
from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    """Parse CORS origins from string or list."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


# Define environment types
class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# Determine environment
def get_environment() -> Environment:
    """Get the current environment."""
    match os.getenv("APP_ENV", "development").lower():
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


# Load appropriate .env file based on environment
def load_env_file():
    """Load environment-specific .env file."""
    env = get_environment()
    base_dir = Path(__file__).parent.parent.parent

    env_files = [
        base_dir / f".env.{env.value}.local",
        base_dir / f".env.{env.value}",
        base_dir / ".env.local",
        base_dir / ".env",
    ]

    for env_file in env_files:
        if env_file.is_file():
            load_dotenv(dotenv_path=env_file)
            return env_file
    return None


ENV_FILE = load_env_file()


# Parse list values from environment variables
def parse_list_from_env(env_key: str, default: Optional[List[str]] = None) -> List[str]:
    """Parse a comma-separated list from an environment variable."""
    value = os.getenv(env_key)
    if not value:
        return default or []
    value = value.strip("\"'")
    if "," not in value:
        return [value]
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application settings using Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE else None,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Environment = get_environment()

    # Application Settings
    PROJECT_NAME: str = "TerraChatBi"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A production-ready FastAPI template with LangGraph and Langfuse integration"
    CONTEXT_PATH: str = ""
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALLOWED_HOSTS: str = "*"
    FRONTEND_HOST: str = "http://localhost:5173"
    DEBUG: bool = False

    # CORS Settings
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []
    ALLOWED_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """Get all CORS origins including frontend host."""
        origins = [str(origin).rstrip("/")
                   for origin in self.BACKEND_CORS_ORIGINS]
        if self.ALLOWED_ORIGINS:
            origins.extend([str(origin).rstrip("/")
                           for origin in self.ALLOWED_ORIGINS])
        if self.FRONTEND_HOST:
            origins.append(self.FRONTEND_HOST.rstrip("/"))
        return origins

    @computed_field  # type: ignore[prop-decorator]
    @property
    def API_V1_STR(self) -> str:
        """Get API version string with context path."""
        return self.CONTEXT_PATH + "/api/v1"

    # Langfuse Settings
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 15432
    POSTGRES_USER: str = "root"
    POSTGRES_PASSWORD: str = "Password123@pg"
    POSTGRES_DB: str = "terra-chatbi"
    TERRA_DB_URL: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get database URI from env or build from components."""
        if self.TERRA_DB_URL:
            return self.TERRA_DB_URL
        return f"postgresql+psycopg://{urllib.parse.quote(self.POSTGRES_USER)}:{urllib.parse.quote(self.POSTGRES_PASSWORD)}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # JWT Configuration
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    DEFAULT_PWD: str = "Terra@123456"
    ASSISTANT_TOKEN_KEY: str = "X-TERRA-ASSISTANT-TOKEN"

    # Cache Settings
    CACHE_TYPE: str = "memory"
    CACHE_REDIS_URL: Optional[str] = None

    # Logging Configuration
    LOG_DIR: Path = Path("logs")
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "console"
    SQL_DEBUG: bool = False

    @field_validator("SQL_DEBUG", mode="before")
    @classmethod
    def parse_bool(cls, v: Any) -> bool:
        """Parse boolean from string."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "t", "yes")
        return bool(v)

    # Base Directory Settings
    BASE_DIR: str = "/opt/terra-chatbi"
    SCRIPT_DIR: str = "/opt/terra-chatbi/scripts"
    UPLOAD_DIR: str = "/opt/terra-chatbi/data/file"

    # License Settings
    SQLBOT_KEY_EXPIRED: int = 100

    # MCP/Image Settings
    MCP_IMAGE_PATH: str = "/opt/terra-chatbi/images"
    EXCEL_PATH: str = "/opt/terra-chatbi/data/excel"
    MCP_IMAGE_HOST: str = "http://localhost:3000"
    SERVER_IMAGE_HOST: str = "http://YOUR_SERVE_IP:MCP_PORT/images/"
    SERVER_IMAGE_TIMEOUT: int = 15

    # SQL Generation Settings
    GENERATE_SQL_QUERY_LIMIT_ENABLED: bool = True
    GENERATE_SQL_QUERY_HISTORY_ROUND_COUNT: int = 3

    # PostgreSQL Pool Settings
    PG_POOL_SIZE: int = 20
    PG_MAX_OVERFLOW: int = 30
    PG_POOL_RECYCLE: int = 3600
    PG_POOL_PRE_PING: bool = True

    @field_validator("PG_POOL_PRE_PING", mode="before")
    @classmethod
    def parse_pool_pre_ping(cls, v: Any) -> bool:
        """Parse pool pre ping boolean."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "t", "yes")
        return bool(v)

    # Rate Limiting Settings
    # Rate limit endpoints defaults
    _default_endpoints: ClassVar[dict[str, list[str]]] = {
        "chat": ["30 per minute"],
        "chat_stream": ["20 per minute"],
        "messages": ["50 per minute"],
        "register": ["10 per hour"],
        "login": ["20 per minute"],
        "root": ["10 per minute"],
        "health": ["20 per minute"],
    }
    RATE_LIMIT_ENDPOINTS: dict[str, list[str]] = {}
    RATE_LIMIT_DEFAULT: list[str] = ["100 per day", "20 per hour"]

    def model_post_init(self, __context: Any) -> None:
        """Apply environment-specific settings after initialization."""
        # Initialize rate limit endpoints from defaults and environment
        self.RATE_LIMIT_ENDPOINTS = self._default_endpoints.copy()
        for endpoint in self._default_endpoints:
            env_key = f"RATE_LIMIT_{endpoint.upper()}"
            value = parse_list_from_env(env_key)
            if value:
                self.RATE_LIMIT_ENDPOINTS[endpoint] = value
        self.apply_environment_settings()

    def apply_environment_settings(self) -> None:
        """Apply environment-specific settings based on the current environment."""
        env_settings = {
            Environment.DEVELOPMENT: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "json",
                "RATE_LIMIT_DEFAULT": ["1000 per day", "200 per hour"],
            },
            Environment.STAGING: {
                "DEBUG": False,
                "LOG_LEVEL": "INFO",
                "RATE_LIMIT_DEFAULT": ["500 per day", "100 per hour"],
            },
            Environment.PRODUCTION: {
                "DEBUG": False,
                "LOG_LEVEL": "WARNING",
                "RATE_LIMIT_DEFAULT": ["200 per day", "50 per hour"],
            },
            Environment.TEST: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
                # Relaxed for testing
                "RATE_LIMIT_DEFAULT": ["1000 per day", "1000 per hour"],
            },
        }

        current_env_settings = env_settings.get(self.ENVIRONMENT, {})
        for key, value in current_env_settings.items():
            env_var_name = key.upper()
            if env_var_name not in os.environ:
                setattr(self, key, value)


# Create settings instance
settings = Settings()
settings.apply_environment_settings()
