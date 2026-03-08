"""Cache module for FastAPI application.

Provides caching decorators and utilities with support for in-memory and Redis backends.
"""

import re
from functools import partial, wraps
from inspect import signature
from typing import Any, Dict, Optional, Tuple

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache as original_cache

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil


def custom_key_builder(
    func: Any,
    namespace: str = "",
    *,
    args: Tuple[Any, ...] = (),
    kwargs: Dict[str, Any],
    cache_name: str,
    key_expression: Optional[str] = None,
) -> str | list[str]:
    """Build cache key from function arguments.

    Args:
        func: The function being cached
        namespace: Cache namespace
        args: Function positional arguments
        kwargs: Function keyword arguments
        cache_name: Name of the cache
        key_expression: Expression to extract key from arguments (e.g., "args[0]" or "user.id")

    Returns:
        Cache key string or list of keys
    """
    try:
        base_key = f"{namespace}:{cache_name}:"

        if key_expression:
            sig = signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            # Support args[0] format
            if key_expression.startswith("args["):
                if match := re.match(r"args\[(\d+)\]", key_expression):
                    index = int(match.group(1))
                    value = bound_args.args[index]
                    if isinstance(value, list):
                        return [f"{base_key}{v}" for v in value]
                    return f"{base_key}{value}"

            # Support attribute path format (e.g., "user.id")
            parts = key_expression.split(".")
            if not bound_args.arguments.get(parts[0]):
                return f"{base_key}{parts[0]}"
            value = bound_args.arguments[parts[0]]
            for part in parts[1:]:
                value = getattr(value, part)
            if isinstance(value, list):
                return [f"{base_key}{v}" for v in value]
            return f"{base_key}{value}"

        # Default to first argument as key
        return f"{base_key}{args[0] if args else 'default'}"

    except Exception as e:
        TerraLogUtil.error("cache_key_builder_error", error=str(e))
        raise ValueError(f"Invalid cache key generation: {e}") from e


def cache(
    expire: int = 60 * 60 * 24,
    namespace: str = "",
    *,
    cache_name: str,
    key_expression: Optional[str] = None,
):
    """Cache decorator with custom key building.

    Args:
        expire: Cache expiration time in seconds (default: 24 hours)
        namespace: Cache namespace
        cache_name: Required name for the cache
        key_expression: Expression to extract cache key from arguments

    Example:
        @cache(expire=3600, cache_name="user", key_expression="user_id")
        async def get_user(user_id: int):
            return await fetch_user(user_id)
    """

    def decorator(func):
        # Pre-build key builder
        used_key_builder = partial(
            custom_key_builder,
            cache_name=cache_name,
            key_expression=key_expression,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if (
                not settings.CACHE_TYPE
                or settings.CACHE_TYPE.lower() == "none"
                or not is_cache_initialized()
            ):
                return await func(*args, **kwargs)

            # Generate cache key
            cache_key = used_key_builder(
                func=func,
                namespace=str(namespace) if namespace else "",
                args=args,
                kwargs=kwargs,
            )

            return await original_cache(
                expire=expire,
                namespace=str(namespace) if namespace else "",
                key_builder=lambda *_, **__: cache_key,
            )(func)(*args, **kwargs)

        return wrapper

    return decorator


def clear_cache(
    namespace: str = "",
    *,
    cache_name: str,
    key_expression: Optional[str] = None,
):
    """Decorator to clear cache after function execution.

    Args:
        namespace: Cache namespace
        cache_name: Required name for the cache
        key_expression: Expression to extract cache key from arguments

    Example:
        @clear_cache(namespace="api", cache_name="user", key_expression="user_id")
        async def update_user(user_id: int, data: dict):
            return await save_user(user_id, data)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if (
                not settings.CACHE_TYPE
                or settings.CACHE_TYPE.lower() == "none"
                or not is_cache_initialized()
            ):
                return await func(*args, **kwargs)

            cache_key = custom_key_builder(
                func=func,
                namespace=str(namespace) if namespace else "",
                args=args,
                kwargs=kwargs,
                cache_name=cache_name,
                key_expression=key_expression,
            )

            key_list = cache_key if isinstance(
                cache_key, list) else [cache_key]
            backend = FastAPICache.get_backend()

            for temp_cache_key in key_list:
                if await backend.get(temp_cache_key):
                    if settings.CACHE_TYPE.lower() == "redis":
                        redis = backend.redis
                        await redis.delete(temp_cache_key)
                    else:
                        await backend.clear(key=temp_cache_key)
                    TerraLogUtil.debug("cache_cleared", key=temp_cache_key)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def init_cache():
    """Initialize cache backend based on settings."""
    cache_type = settings.CACHE_TYPE

    if cache_type == "memory":
        FastAPICache.init(InMemoryBackend())
        TerraLogUtil.info("cache_initialized",
                          backend="memory", mode="single_process")
    elif cache_type == "redis":
        from fastapi_cache.backends.redis import RedisBackend
        import redis.asyncio as redis
        from redis.asyncio.connection import ConnectionPool

        redis_url = settings.CACHE_REDIS_URL or "redis://localhost:6379/0"
        pool = ConnectionPool.from_url(url=redis_url)
        redis_client = redis.Redis(connection_pool=pool)
        FastAPICache.init(RedisBackend(redis_client), prefix="terra-cache")
        TerraLogUtil.info(
            "cache_initialized", backend="redis", mode="multi_process", url=redis_url
        )
    else:
        TerraLogUtil.warning("cache_disabled", mode="multi_process")


def is_cache_initialized() -> bool:
    """Check if cache has been initialized.

    Returns:
        True if cache is initialized and ready to use
    """
    # Check required attributes exist
    if not hasattr(FastAPICache, "_backend") or not hasattr(FastAPICache, "_prefix"):
        return False

    # Check attribute values are not None
    if FastAPICache._backend is None or FastAPICache._prefix is None:
        return False

    # Try to get backend to confirm
    try:
        backend = FastAPICache.get_backend()
        return backend is not None
    except (AssertionError, AttributeError, Exception) as e:
        TerraLogUtil.debug("cache_init_check_failed", error=str(e))
        return False
