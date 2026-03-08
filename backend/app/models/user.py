"""This file contains the user model for the application."""

import bcrypt
from sqlmodel import (
    Field,
    Relationship,
    BigInteger,
)

from app.models.base import BaseModel
from app.core.common.config import settings


def default_hash_password():
    """Return the default hashed password."""
    return UserModel.hash_password(settings.DEFAULT_PWD)


class UserModel(BaseModel, table=True):
    """User model for storing user accounts.

    Attributes:
        id: The primary key
        email: User's email (unique)
        hashed_password: Bcrypt hashed password
        created_at: When the user was created
        sessions: Relationship to user's chat sessions
    """
    __tablename__ = "users"
    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field(
        nullable=False, default_factory=default_hash_password)
    oid: int = Field(nullable=False, sa_type=BigInteger())  # 现在绑定的workspace id
    status: int = Field(default=1, nullable=False)

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


class WorkSpaceModel(BaseModel, table=True):
    """Workspace model for storing workspaces.
    Attributes:
        id: The primary key
        name: Workspace's name (unique)
        description: Workspace's description
    """
    __tablename__ = "workspaces"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str = Field(default="")


class WorkspaceUserModel(BaseModel, table=True):
    """WorkspaceUser model for storing workspace users.
    Attributes:
        id: The primary key
        workspace_id: The workspace id
        user_id: The user id
    """
    __tablename__ = "workspace_users"
    id: int = Field(default=None, primary_key=True)
    uid: int = Field(nullable=False, sa_type=BigInteger())
    oid: int = Field(nullable=False, sa_type=BigInteger())
    role: int = Field(default=0, nullable=False)  # 0: member, 1: admin
