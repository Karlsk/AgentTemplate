"""Permission decorators for FastAPI endpoints."""

from functools import wraps
from typing import List, Union

from fastapi import HTTPException, Request, status

from app.core.common.deps import get_current_user_from_state
from app.core.common.logging import TerraLogUtil


def require_permissions(roles: Union[str, List[str]]):
    """Decorator to require specific roles for accessing an endpoint.

    Args:
        roles: Single role string or list of role strings (e.g., 'admin', 'member', or ['admin', 'member'])

    Raises:
        HTTPException: 403 Forbidden if user doesn't have required role
        HTTPException: 401 Unauthorized if user is not authenticated

    Example:
        @require_permissions('admin')
        async def delete_workspace(request: Request, ...)

        @require_permissions(['admin', 'member'])
        async def view_workspace(request: Request, ...)
    """
    if isinstance(roles, str):
        roles = [roles]

    # Normalize roles to lowercase for comparison
    required_roles = set(r.lower() for r in roles)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get current_user from kwargs (injected by FastAPI dependencies)
            current_user = kwargs.get('current_user')
            TerraLogUtil.info(
                "require_permissions_check",
                has_current_user=current_user is not None,
                user_type=type(current_user).__name__ if current_user else None
            )
            # If not in kwargs, try to find from args (in case it's a positional argument)
            if current_user is None:
                for arg in args:
                    if hasattr(arg, 'id') and hasattr(arg, 'email'):
                        current_user = arg
                        break

            # If still not found, try to get from request.state
            if current_user is None:
                # Find request object from args or kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if request is None:
                    request = kwargs.get('request')

                if request is not None:
                    current_user = get_current_user_from_state(request)

            if current_user is None:
                TerraLogUtil.warning(
                    "require_permissions_auth_required",
                    kwargs_keys=list(kwargs.keys())
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check if user is the default admin (dms@admin.com)
            # Handle both UserModel object and user dict from token
            if isinstance(current_user, dict):
                user_email = current_user.get('email')
            else:
                user_email = getattr(current_user, 'email', None)
            is_default_admin = user_email == "dms@admin.com"

            # If 'admin' is required, only default admin has permission
            if 'admin' in required_roles:
                if not is_default_admin:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Admin permission required"
                    )

            # For 'member' role or other roles, temporarily allow all authenticated users
            # (member implementation pending)

            return await func(*args, **kwargs)

        return wrapper
    return decorator
