"""This file contains the authentication schema for the application."""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)
from typing import List, Optional

from app.schemas.base import BaseEditDTO


class Token(BaseModel):
    """Token model for authentication.

    Attributes:
        access_token: The JWT access token.
        token_type: The type of token (always "bearer").
        expires_at: The token expiration timestamp.
    """

    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(...,
                                 description="The token expiration timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseUser(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    oid: int = Field(..., description="Workspace ID")


class PwdEditor(BaseModel):
    password: SecretStr = Field(..., description="User's password")
    new_password: SecretStr = Field(..., description="User's new password")

    @field_validator("password", "new_password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        """Validate password strength.

        Args:
            v: The password to validate

        Returns:
            SecretStr: The validated password

        Raises:
            ValueError: If the password is not strong enough
        """
        password = v.get_secret_value()

        # Check for common password requirements
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", password):
            raise ValueError(
                "Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            raise ValueError(
                "Password must contain at least one lowercase letter")

        if not re.search(r"[0-9]", password):
            raise ValueError("Password must contain at least one number")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError(
                "Password must contain at least one special character")

        return v


class UserCreator(BaseUser):
    """Request model for user registration.

    Attributes:
        email: User's email address
        password: User's password
    """
    status: int = Field(
        default=1, description="User's status")  # 1: active, 0: inactive
    oid_list: Optional[list[int]] = Field(
        default=None, description="Workspace ID列表")


class UserStatus(BaseEditDTO):
    id: int = Field(..., description="User's ID")
    status: int = Field(default=1, description=f"user_status")


class UserResponse(BaseEditDTO):
    """Response model for user operations.

    Attributes:
        id: User's ID
        email: User's email address
        token: Authentication token
    """

    email: str = Field(..., description="User's email address")
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(...,
                                 description="The token expiration timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserInfoResponse(BaseModel):
    """Response model for user info (without token).

    Attributes:
        id: User's ID
        email: User's email address
        oid: Current workspace ID
        status: User status
        created_at: Creation timestamp
    """

    id: int = Field(..., description="User's ID")
    email: str = Field(..., description="User's email address")
    oid: int = Field(..., description="Current workspace ID")
    status: int = Field(..., description="User status")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkspaceCreator(BaseModel):
    """Request model for workspace creation.

    Attributes:
        name: Workspace name (unique)
        description: Workspace description
    """

    name: str = Field(..., description="Workspace name",
                      min_length=1, max_length=100)
    description: str = Field(
        default="", description="Workspace description", max_length=500)


class WorkspaceResponse(BaseModel):
    """Response model for workspace operations.

    Attributes:
        id: Workspace ID
        name: Workspace name
        description: Workspace description
        created_at: Creation timestamp
    """

    id: int = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    description: str = Field(default="", description="Workspace description")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkspaceUserRelation(BaseModel):
    """Request model for workspace-user relation operations.

    Attributes:
        uid_list: List of User IDs
        oid: Workspace ID
        role: Role (0=member, 1=admin)
    """

    uid_list: List[int] = Field(..., description="User ID 列表", min_length=1)
    oid: int = Field(..., description="Workspace ID")
    role: int = Field(default=0, description="Role: 0=member, 1=admin")


class WorkspaceUserResponse(BaseModel):
    """Response model for workspace-user relation.

    Attributes:
        id: Relation ID
        uid: User ID
        oid: Workspace ID
        role: Role
        created_at: Creation timestamp
    """

    id: int = Field(..., description="Relation ID")
    uid: int = Field(..., description="User ID")
    oid: int = Field(..., description="Workspace ID")
    role: int = Field(..., description="Role: 0=member, 1=admin")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionResponse(BaseModel):
    """Response model for session creation.

    Attributes:
        session_id: The unique identifier for the chat session
        name: Name of the session (defaults to empty string)
        token: The authentication token for the session
    """

    session_id: str = Field(...,
                            description="The unique identifier for the chat session")
    name: str = Field(
        default="", description="Name of the session", max_length=100)
    token: Token = Field(...,
                         description="The authentication token for the session")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Sanitize the session name.

        Args:
            v: The name to sanitize

        Returns:
            str: The sanitized name
        """
        # Remove any potentially harmful characters
        sanitized = re.sub(r'[<>{}[\]()\'"`]', "", v)
        return sanitized


class SwitchWorkspaceRequest(BaseModel):
    """Request model for switching user's current workspace.

    Attributes:
        workspace_id: Target workspace ID to switch to
    """

    workspace_id: int = Field(..., description="Target workspace ID")
