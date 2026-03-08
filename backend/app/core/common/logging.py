"""Logging configuration and setup for the application.

This module provides structured logging configuration using standard logging,
with environment-specific formatters and handlers. It supports both
console-friendly development logging and file-based production logging.
"""

import inspect
import logging
import sys
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

from app.core.common.config import (
    Environment,
    settings,
)


# Context variables for storing request-specific data
_request_context: ContextVar[Dict[str, Any]] = ContextVar(
    "request_context", default={})


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the current request.

    Args:
        **kwargs: Key-value pairs to bind to the logging context
    """
    current = _request_context.get()
    _request_context.set({**current, **kwargs})


def clear_context() -> None:
    """Clear all context variables for the current request."""
    _request_context.set({})


def get_context() -> Dict[str, Any]:
    """Get the current logging context.

    Returns:
        Dict[str, Any]: Current context dictionary
    """
    return _request_context.get()


def add_context_to_event_dict(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add context variables to the event dictionary.

    This processor adds any bound context variables to each log event.

    Args:
        logger: The logger instance
        method_name: The name of the logging method
        event_dict: The event dictionary to modify

    Returns:
        Dict[str, Any]: Modified event dictionary with context variables
    """
    context = get_context()
    if context:
        event_dict.update(context)
    return event_dict


class ContextFilter(logging.Filter):
    """Filter that adds context variables to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context variables to the log record."""
        context = get_context()
        if context:
            # Add context as extra attributes
            for key, value in context.items():
                if not hasattr(record, key):
                    setattr(record, key, value)
        return True


def setup_logging():
    """Configure logging with different handlers based on environment."""
    # Ensure log directory exists
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Parse log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Log format - include context variables
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Context filter to add context variables
    context_filter = ContextFilter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)

    # File handlers for different levels
    file_handlers = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'error': logging.ERROR
    }

    # Main logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set minimum level

    # Add console handler
    root_logger.addHandler(console_handler)

    # Create file handlers for each level
    for level_name, level in file_handlers.items():
        file_path = log_dir / f"{level_name}.log"
        handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        handler.addFilter(context_filter)

        # Add filter to only handle specific level logs
        if level_name == 'debug':
            handler.addFilter(lambda record: record.levelno == logging.DEBUG)
        elif level_name == 'info':
            handler.addFilter(lambda record: record.levelno == logging.INFO)
        elif level_name == 'warn':
            handler.addFilter(lambda record: record.levelno == logging.WARNING)
        elif level_name == 'error':
            handler.addFilter(lambda record: record.levelno >= logging.ERROR)

        root_logger.addHandler(handler)

    # SQL logging special handling
    if settings.LOG_LEVEL.upper() == "DEBUG" and settings.SQL_DEBUG:
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.DEBUG)

        sql_handler = RotatingFileHandler(
            log_dir / "sql.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=2,
            encoding='utf-8'
        )
        sql_handler.setFormatter(formatter)
        sql_handler.addFilter(context_filter)
        sql_logger.addHandler(sql_handler)

    # Set alembic logger levels to prevent them from changing root logger level
    alembic_logger = logging.getLogger('alembic')
    alembic_logger.setLevel(log_level)
    alembic_runtime_logger = logging.getLogger('alembic.runtime.migration')
    alembic_runtime_logger.setLevel(log_level)


class CallerLogger(logging.Logger):
    """Logger wrapper that preserves caller information."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        super().__init__(logger.name, logger.level)

    def _log(self, level, msg, args, exc_info=None, extra=None, stacklevel=3, **kwargs):
        if self.logger.isEnabledFor(level):
            # Format kwargs as key=value pairs for the log message
            if kwargs:
                kv_pairs = [f"{k}={v}" for k, v in kwargs.items()]
                msg = f"{msg} {' '.join(kv_pairs)}"

            # Add context to extra if not present
            context = get_context()
            if context:
                if extra is None:
                    extra = {}
                for key, value in context.items():
                    if key not in extra:
                        extra[key] = value
            self.logger._log(level, msg, args, exc_info=exc_info,
                             extra=extra, stacklevel=stacklevel)


class TerraLogUtil:
    """Static utility class for convenient logging.

    Provides a simple static interface with automatic caller module detection.

    Example:
        TerraLogUtil.info("user_login_successful", user_id=123, ip="192.168.1.1")
        TerraLogUtil.error("database_connection_failed", retry_count=3, exc_info=True)
    """

    @staticmethod
    def _get_logger() -> CallerLogger:
        """Get a logger for the caller's module."""
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back.f_back
            module_name = caller_frame.f_globals.get('__name__', '__main__')
            return CallerLogger(logging.getLogger(module_name))
        finally:
            del frame

    @staticmethod
    def debug(msg: str, *args, **kwargs):
        """Log a debug message."""
        logger = TerraLogUtil._get_logger()
        if logger.isEnabledFor(logging.DEBUG):
            logger._log(logging.DEBUG, msg, args, **kwargs)

    @staticmethod
    def info(msg: str, *args, **kwargs):
        """Log an info message."""
        logger = TerraLogUtil._get_logger()
        if logger.isEnabledFor(logging.INFO):
            logger._log(logging.INFO, msg, args, **kwargs)

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        """Log a warning message."""
        logger = TerraLogUtil._get_logger()
        if logger.isEnabledFor(logging.WARNING):
            logger._log(logging.WARNING, msg, args, **kwargs)

    @staticmethod
    def error(msg: str, *args, exc_info: Optional[bool] = None, **kwargs):
        """Log an error message."""
        logger = TerraLogUtil._get_logger()
        if logger.isEnabledFor(logging.ERROR):
            logger._log(
                logging.ERROR,
                msg,
                args,
                exc_info=exc_info if exc_info is not None else True,
                **kwargs
            )

    @staticmethod
    def exception(msg: str, *args, **kwargs):
        """Log an exception message with traceback."""
        logger = TerraLogUtil._get_logger()
        if logger.isEnabledFor(logging.ERROR):
            logger._log(logging.ERROR, msg, args, exc_info=True, **kwargs)

    @staticmethod
    def critical(msg: str, *args, **kwargs):
        """Log a critical message."""
        logger = TerraLogUtil._get_logger()
        if logger.isEnabledFor(logging.CRITICAL):
            logger._log(logging.CRITICAL, msg, args, **kwargs)


# Initialize logging
setup_logging()

# Log initialization complete
log_level_name = settings.LOG_LEVEL
TerraLogUtil.info(
    "logging_initialized",
    environment=settings.ENVIRONMENT.value,
    log_level=log_level_name,
    log_format=settings.LOG_FORMAT,
    debug=settings.DEBUG,
)
