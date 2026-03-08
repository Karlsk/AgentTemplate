from re import U
from fastapi import Depends, Request, status
from sqlmodel import Session
from typing import Annotated

from app.core.common.db import get_session
from app.core.common.logging import TerraLogUtil
from app.models.user import UserModel
from app.models.session import SessionModel

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user_from_state(request: Request):
    """Get current user from request state.

    Args:
        request: The FastAPI request object

    Returns:
        The UserModel instance or user dict if authenticated

    Raises:
        HTTPException: 401 if not authenticated
    """
    user = getattr(request.state, "user", None)
    user_id = getattr(request.state, "user_id", None)
    session = getattr(request.state, "session", None)

    if user is None:
        from fastapi import HTTPException
        TerraLogUtil.warning(
            "get_current_user_from_state_auth_required",
            user_id=user_id,
            has_session=session is not None,
            path=request.url.path,
            auth_header=request.headers.get("Authorization", "not_present")
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_session_from_state(request: Request):
    """Get current session from request state.

    Args:
        request: The FastAPI request object

    Returns:
        The SessionModel instance if authenticated

    Raises:
        HTTPException: 401 if not authenticated with session
    """
    session = getattr(request.state, "session", None)
    user_id = getattr(request.state, "user_id", None)

    if session is None:
        from fastapi import HTTPException
        TerraLogUtil.warning(
            "get_current_session_from_state_auth_required",
            user_id=user_id,
            path=request.url.path,
            auth_header=request.headers.get("Authorization", "not_present"),
            session_header=request.headers.get("X-Session-Id", "not_present")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


CurrentUser = Annotated[UserModel, Depends(get_current_user_from_state)]
CurrentSession = Annotated[SessionModel,
                           Depends(get_current_session_from_state)]
