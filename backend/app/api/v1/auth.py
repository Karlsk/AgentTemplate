"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
token verification, user management, and workspace management.
"""

import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlmodel import Session

from app.core.common.config import settings
from app.core.common.limiter import limiter
from app.core.common.logging import (
    bind_context,
    TerraLogUtil,
)
from app.models.session import SessionModel
from app.models.user import UserModel
from app.schemas.auth import (
    SessionResponse,
    UserCreator,
    UserInfoResponse,
    UserResponse,
    Token as TokenResponse,
    WorkspaceCreator,
    WorkspaceResponse,
    WorkspaceUserRelation,
    WorkspaceUserResponse,
    SwitchWorkspaceRequest,
    PwdEditor,
    UserStatus,
)

from app.services.auth import AuthService
from app.utils.auth import (
    create_access_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)
from app.core.common.deps import CurrentUser, SessionDep
from app.core.common.permissions import require_permissions

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, description="Register a new user")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def register_user(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    user_data: UserCreator,
):
    """Register a new user.

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User registration data

    Returns:
        UserResponse: The created user info
    """
    try:
        # Sanitize email
        sanitized_email = sanitize_email(user_data.email)

        # Check if user exists
        if await auth_service.get_user_by_email(session=session, email=sanitized_email):
            raise HTTPException(
                status_code=400, detail="Email already registered")

        # Create user
        user: UserModel = await auth_service.create_user(session=session, creator=user_data)

        # Create access token with user data
        token = create_access_token(
            thread_id=str(user.id),
            user_data={
                "id": user.id,
                "email": user.email,
                "oid": user.oid,
                "status": user.status
            }
        )

        # Return as dict to avoid serialization issues
        return {
            "id": user.id,
            "email": user.email,
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_at": token.expires_at.isoformat()
        }
    except ValueError as ve:
        TerraLogUtil.error("user_registration_validation_failed",
                           error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request,
    session: SessionDep,
    username: str = Form(...),
    password: str = Form(...),
    grant_type: str = Form(default="password"),
):
    """Login a user.

    Args:
        request: The FastAPI request object for rate limiting.
        username: User's email
        password: User's password
        grant_type: Must be "password"

    Returns:
        TokenResponse: Access token information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Sanitize inputs
        username = sanitize_string(username)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)

        # Verify grant type
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user: UserModel = await auth_service.get_user_by_email(session=session, email=username)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token with user data
        token = create_access_token(
            thread_id=str(user.id),
            user_data={
                "id": user.id,
                "email": user.email,
                "oid": user.oid,
                "status": user.status
            }
        )
        return TokenResponse(access_token=token.access_token, token_type="bearer", expires_at=token.expires_at)
    except ValueError as ve:
        TerraLogUtil.error("login_validation_failed",
                           error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


# ============================================================
# User Management Endpoints
# ============================================================

@router.get("/users", response_model=List[UserInfoResponse], description="Get all users")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def get_users(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Get all users.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.

    Returns:
        List[UserInfoResponse]: List of all users.
    """
    users = await auth_service.get_all_users(session=session)
    TerraLogUtil.info("get_all_users", count=len(users))
    return [
        {
            "id": u.id,
            "email": u.email,
            "oid": u.oid,
            "status": u.status,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.get("/users/by-email", response_model=UserInfoResponse, description="Get user by email")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def get_user_by_email(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    email: str,
):
    """Get a user by email address.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        email: The email to look up.

    Returns:
        UserInfoResponse: The found user.

    Raises:
        HTTPException: 404 if user not found.
    """
    sanitized_email = sanitize_email(email)
    user = await auth_service.get_user_by_email(session=session, email=sanitized_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    TerraLogUtil.info("get_user_by_email",
                      email=sanitized_email, user_id=user.id)
    return {
        "id": user.id,
        "email": user.email,
        "oid": user.oid,
        "status": user.status,
        "created_at": user.created_at,
    }


@router.patch("/users/me/password", description="Change current user's password")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def change_password(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    body: PwdEditor,
):
    """Change the current user's password.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated user (user_id taken from here).
        session: The database session.
        body: Request body containing old password and new password.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: 404 if user not found.
        HTTPException: 401 if old password is incorrect.
    """
    ok, reason = await auth_service.change_password(
        session=session,
        user_id=current_user.id,
        old_password=body.password.get_secret_value(),
        new_password=body.new_password.get_secret_value(),
    )
    if not ok:
        if reason == "not_found":
            raise HTTPException(status_code=404, detail="User not found")
        if reason == "wrong_password":
            raise HTTPException(
                status_code=401, detail="Current password is incorrect")
    TerraLogUtil.info("user_password_changed", user_id=current_user.id)
    return {"message": "Password changed successfully"}


@router.patch("/users/status", description="Update user status (admin only)")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def update_user_status(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    body: UserStatus,
):
    """Update a user's status.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        body: Request body containing user_id and target status.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: 404 if user not found.
        HTTPException: 403 if target user is the default admin.
    """
    ok, reason = await auth_service.update_user_status(
        session=session,
        user_id=body.id,
        status=body.status,
    )
    if not ok:
        if reason == "not_found":
            raise HTTPException(status_code=404, detail="User not found")
        if reason == "admin_protected":
            raise HTTPException(
                status_code=403, detail="Cannot modify the default admin user's status")
    TerraLogUtil.info("user_status_updated",
                      user_id=body.id, status=body.status)
    return {"message": "User status updated successfully", "user_id": body.id, "status": body.status}


@router.delete("/users/{user_id}", description="Delete a user by ID")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def delete_user(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    user_id: int,
):
    """Delete a user by ID.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        user_id: The ID of the user to delete.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: 404 if user not found.
    """
    deleted, reason = await auth_service.delete_user(session=session, user_id=user_id)
    if not deleted:
        if reason == "not_found":
            raise HTTPException(status_code=404, detail="User not found")
        if reason == "admin_protected":
            raise HTTPException(
                status_code=403, detail="Cannot delete the default admin user")
    TerraLogUtil.info("user_deleted", user_id=user_id)
    return {"message": "User deleted successfully", "user_id": user_id}


# ============================================================
# Workspace Management Endpoints
# ============================================================

@router.post("/workspaces", response_model=WorkspaceResponse, description="Create a new workspace")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def create_workspace(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    workspace_data: WorkspaceCreator,
):
    """Create a new workspace.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        workspace_data: Workspace creation data.

    Returns:
        WorkspaceResponse: The created workspace.

    Raises:
        HTTPException: 400 if workspace name already exists.
    """
    try:
        workspace = await auth_service.create_workspace(session=session, creator=workspace_data)
        TerraLogUtil.info("workspace_created",
                          workspace_id=workspace.id, name=workspace.name)
        return {
            "id": workspace.id,
            "name": workspace.name,
            "description": workspace.description,
            "created_at": workspace.created_at,
        }
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=400, detail="Workspace name already exists")
        TerraLogUtil.exception("workspace_creation_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to create workspace")


@router.get("/workspaces", response_model=List[WorkspaceResponse], description="Get all workspaces")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def get_workspaces(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Get all workspaces.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.

    Returns:
        List[WorkspaceResponse]: List of all workspaces.
    """
    workspaces = await auth_service.get_all_workspaces(session=session)
    TerraLogUtil.info("get_all_workspaces", count=len(workspaces))
    return [
        {
            "id": ws.id,
            "name": ws.name,
            "description": ws.description,
            "created_at": ws.created_at,
        }
        for ws in workspaces
    ]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, description="Get workspace by ID")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def get_workspace_by_id(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    workspace_id: int,
):
    """Get a workspace by ID.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        workspace_id: The workspace ID to look up.

    Returns:
        WorkspaceResponse: The found workspace.

    Raises:
        HTTPException: 404 if workspace not found.
    """
    workspace = await auth_service.get_workspace_by_id(session=session, workspace_id=workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    TerraLogUtil.info("get_workspace_by_id", workspace_id=workspace_id)
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at,
    }


@router.delete("/workspaces/{workspace_id}", description="Delete a workspace by ID")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def delete_workspace(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    workspace_id: int,
):
    """Delete a workspace by ID.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        workspace_id: The ID of the workspace to delete.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: 404 if workspace not found.
    """
    deleted, reason = await auth_service.delete_workspace(session=session, workspace_id=workspace_id)
    if not deleted:
        if reason == "not_found":
            raise HTTPException(status_code=404, detail="Workspace not found")
        if reason == "has_users":
            raise HTTPException(
                status_code=409, detail="Cannot delete workspace with associated users, please remove all users first")
    TerraLogUtil.info("workspace_deleted", workspace_id=workspace_id)
    return {"message": "Workspace deleted successfully", "workspace_id": workspace_id}


# ============================================================
# Workspace-User Relation Endpoints
# ============================================================

@router.post("/workspaces/{workspace_id}/users", response_model=List[WorkspaceUserResponse], description="Batch add users to workspace")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def add_user_to_workspace(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    workspace_id: int,
    relation: WorkspaceUserRelation,
):
    """Batch add users to a workspace (or update role if already exists).

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        workspace_id: The workspace ID (must match relation.oid).
        relation: The relation data including uid_list, oid, and role.

    Returns:
        List[WorkspaceUserResponse]: The created/updated relations.

    Raises:
        HTTPException: 404 if any user or workspace not found.
        HTTPException: 400 if workspace_id and relation.oid mismatch.
    """
    if relation.oid != workspace_id:
        raise HTTPException(
            status_code=400,
            detail="workspace_id in path must match oid in body"
        )
    workspace = await auth_service.get_workspace_by_id(session=session, workspace_id=workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    # Verify all users exist
    for uid in relation.uid_list:
        user = await auth_service.get_db_user(session=session, user_id=uid)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User {uid} not found")

    rels = await auth_service.add_user_to_workspace(
        session=session, uid_list=relation.uid_list, oid=workspace_id, role=relation.role
    )
    TerraLogUtil.info("users_added_to_workspace", uid_list=relation.uid_list,
                      oid=workspace_id, role=relation.role)
    return [
        {
            "id": r.id,
            "uid": r.uid,
            "oid": r.oid,
            "role": r.role,
            "created_at": r.created_at,
        }
        for r in rels
    ]


@router.delete("/workspaces/{workspace_id}/users/{user_id}", description="Remove user from workspace")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def remove_user_from_workspace(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    workspace_id: int,
    user_id: int,
):
    """Remove a user from a workspace.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        workspace_id: The workspace ID.
        user_id: The user ID to remove.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: 404 if relation not found.
    """
    removed = await auth_service.remove_user_from_workspace(
        session=session, uid=user_id, oid=workspace_id
    )
    if not removed:
        raise HTTPException(
            status_code=404, detail="User-workspace relation not found")
    TerraLogUtil.info("user_removed_from_workspace",
                      uid=user_id, oid=workspace_id)
    return {"message": "User removed from workspace successfully", "uid": user_id, "oid": workspace_id}


@router.get("/workspaces/{workspace_id}/users", response_model=List[WorkspaceUserResponse], description="Get all users in a workspace")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def get_workspace_users(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    workspace_id: int,
):
    """Get all users in a workspace.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        workspace_id: The workspace ID.

    Returns:
        List[WorkspaceUserResponse]: List of user relations in the workspace.
    """
    # Verify workspace exists
    workspace = await auth_service.get_workspace_by_id(session=session, workspace_id=workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    relations = await auth_service.get_workspace_users(session=session, oid=workspace_id)
    TerraLogUtil.info("get_workspace_users",
                      oid=workspace_id, count=len(relations))
    return [
        {
            "id": r.id,
            "uid": r.uid,
            "oid": r.oid,
            "role": r.role,
            "created_at": r.created_at,
        }
        for r in relations
    ]


@router.get("/users/{user_id}/workspaces", response_model=List[WorkspaceUserResponse], description="Get all workspaces for a user")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
@require_permissions("admin")
async def get_user_workspaces(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    user_id: int,
):
    """Get all workspaces a user belongs to.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated admin user.
        session: The database session.
        user_id: The user ID.

    Returns:
        List[WorkspaceUserResponse]: List of workspace relations for the user.
    """
    # Verify user exists
    user = await auth_service.get_db_user(session=session, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    relations = await auth_service.get_user_workspaces(session=session, uid=user_id)
    TerraLogUtil.info("get_user_workspaces", uid=user_id, count=len(relations))
    return [
        {
            "id": r.id,
            "uid": r.uid,
            "oid": r.oid,
            "role": r.role,
            "created_at": r.created_at,
        }
        for r in relations
    ]


@router.patch("/users/switch/workspace", response_model=UserInfoResponse, description="Switch current user's workspace")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def switch_user_workspace(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    body: SwitchWorkspaceRequest,
):
    """Switch the current user's active workspace (oid field).

    Admin user (dms@admin.com) can switch to any workspace freely.
    Non-admin users can only switch to a workspace they are associated with.

    Args:
        request: The FastAPI request object.
        current_user: The authenticated user (user_id is taken from here).
        session: The database session.
        body: Request body containing the target workspace_id.

    Returns:
        UserInfoResponse: Updated user info.

    Raises:
        HTTPException: 404 if user or workspace not found.
        HTTPException: 403 if user is not associated with the target workspace.
    """
    user_id = current_user.id
    is_admin = current_user.email == "dms@admin.com"

    ok, reason = await auth_service.switch_user_workspace(
        session=session,
        user_id=user_id,
        workspace_id=body.workspace_id,
        is_admin=is_admin,
    )
    if not ok:
        if reason == "user_not_found":
            raise HTTPException(status_code=404, detail="User not found")
        if reason == "workspace_not_found":
            raise HTTPException(status_code=404, detail="Workspace not found")
        if reason == "not_associated":
            raise HTTPException(
                status_code=403,
                detail="User is not associated with the target workspace"
            )

    user = await auth_service.get_db_user(session=session, user_id=user_id)
    TerraLogUtil.info("user_workspace_switched",
                      user_id=user_id, workspace_id=body.workspace_id)
    return {
        "id": user.id,
        "email": user.email,
        "oid": user.oid,
        "status": user.status,
        "created_at": user.created_at,
    }
