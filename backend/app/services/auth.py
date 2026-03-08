from typing import List, Optional
from sqlmodel import Session, func, select, delete as sqlmodel_delete

from app.models.user import UserModel, WorkSpaceModel, WorkspaceUserModel
from app.models.session import SessionModel
from app.schemas.auth import UserCreator, WorkspaceCreator


class AuthService:
    """Authentication service.
    """

    @staticmethod
    async def get_db_user(*, session: Session, user_id: int) -> Optional[UserModel]:
        user = session.get(UserModel, user_id)
        return user

    @staticmethod
    async def get_db_session(*, session: Session, session_id: int) -> Optional[SessionModel]:
        db_session = session.get(SessionModel, session_id)
        return db_session

    @staticmethod
    async def get_user_by_email(*, session: Session, email: str) -> Optional[UserModel]:
        return session.exec(select(UserModel).where(UserModel.email == email)).first()

    @staticmethod
    async def get_all_users(*, session: Session) -> List[UserModel]:
        return session.exec(select(UserModel)).all()

    @staticmethod
    async def delete_user(*, session: Session, user_id: int) -> tuple[bool, str]:
        """Delete a user by ID.

        Returns:
            (False, "not_found") if user does not exist.
            (False, "admin_protected") if user is the default admin.
            (True, "") on success.
        """
        user = session.get(UserModel, user_id)
        if not user:
            return False, "not_found"
        if user.email == "dms@admin.com":
            return False, "admin_protected"
        # Cascade: remove all workspace relations for this user
        relations = session.exec(
            select(WorkspaceUserModel).where(WorkspaceUserModel.uid == user_id)
        ).all()
        for rel in relations:
            session.delete(rel)
        session.delete(user)
        session.commit()
        return True, ""

    @staticmethod
    async def create_user(*, session: Session, creator: UserCreator) -> UserModel:
        # Get oid from oid_list if provided, otherwise use default (1)
        oid = 1
        if creator.oid_list and len(creator.oid_list) > 0:
            oid = creator.oid_list[0]

        user = UserModel(
            email=creator.email,
            status=creator.status,
            oid=oid,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    # --- Workspace methods ---

    @staticmethod
    async def create_workspace(*, session: Session, creator: WorkspaceCreator) -> WorkSpaceModel:
        workspace = WorkSpaceModel(
            name=creator.name,
            description=creator.description,
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace

    @staticmethod
    async def get_all_workspaces(*, session: Session) -> List[WorkSpaceModel]:
        return session.exec(select(WorkSpaceModel)).all()

    @staticmethod
    async def get_workspace_by_id(*, session: Session, workspace_id: int) -> Optional[WorkSpaceModel]:
        return session.get(WorkSpaceModel, workspace_id)

    @staticmethod
    async def delete_workspace(*, session: Session, workspace_id: int) -> tuple[bool, str]:
        """Delete a workspace by ID.

        Returns:
            (False, "not_found") if workspace does not exist.
            (False, "has_users") if there are users associated with this workspace.
            (True, "") on success.
        """
        workspace = session.get(WorkSpaceModel, workspace_id)
        if not workspace:
            return False, "not_found"
        # Reject deletion if there are associated users
        relations = session.exec(
            select(WorkspaceUserModel).where(
                WorkspaceUserModel.oid == workspace_id)
        ).all()
        if relations:
            return False, "has_users"
        session.delete(workspace)
        session.commit()
        return True, ""

    # --- Workspace-User relation methods ---

    @staticmethod
    async def add_user_to_workspace(
        *, session: Session, uid_list: List[int], oid: int, role: int = 0
    ) -> List[WorkspaceUserModel]:
        results = []
        for uid in uid_list:
            existing = session.exec(
                select(WorkspaceUserModel).where(
                    WorkspaceUserModel.uid == uid,
                    WorkspaceUserModel.oid == oid,
                )
            ).first()
            if existing:
                existing.role = role
                session.add(existing)
                results.append(existing)
            else:
                relation = WorkspaceUserModel(uid=uid, oid=oid, role=role)
                session.add(relation)
                results.append(relation)
        session.commit()
        for r in results:
            session.refresh(r)
        return results

    @staticmethod
    async def remove_user_from_workspace(*, session: Session, uid: int, oid: int) -> bool:
        relation = session.exec(
            select(WorkspaceUserModel).where(
                WorkspaceUserModel.uid == uid,
                WorkspaceUserModel.oid == oid,
            )
        ).first()
        if not relation:
            return False
        session.delete(relation)
        session.commit()
        return True

    @staticmethod
    async def get_workspace_users(*, session: Session, oid: int) -> List[WorkspaceUserModel]:
        return session.exec(
            select(WorkspaceUserModel).where(WorkspaceUserModel.oid == oid)
        ).all()

    @staticmethod
    async def get_user_workspaces(*, session: Session, uid: int) -> List[WorkspaceUserModel]:
        return session.exec(
            select(WorkspaceUserModel).where(WorkspaceUserModel.uid == uid)
        ).all()

    @staticmethod
    async def change_password(
        *, session: Session, user_id: int, old_password: str, new_password: str
    ) -> tuple[bool, str]:
        """Change a user's password.

        Returns:
            (False, "not_found") if user does not exist.
            (False, "wrong_password") if old password is incorrect.
            (True, "") on success.
        """
        user = session.get(UserModel, user_id)
        if not user:
            return False, "not_found"
        if not user.verify_password(old_password):
            return False, "wrong_password"
        user.hashed_password = UserModel.hash_password(new_password)
        session.add(user)
        session.commit()
        return True, ""

    @staticmethod
    async def update_user_status(
        *, session: Session, user_id: int, status: int
    ) -> tuple[bool, str]:
        """Update a user's status.

        Returns:
            (False, "not_found") if user does not exist.
            (False, "admin_protected") if user is the default admin.
            (True, "") on success.
        """
        user = session.get(UserModel, user_id)
        if not user:
            return False, "not_found"
        if user.email == "dms@admin.com":
            return False, "admin_protected"
        user.status = status
        session.add(user)
        session.commit()
        session.refresh(user)
        return True, ""

    @staticmethod
    async def switch_user_workspace(
        *, session: Session, user_id: int, workspace_id: int, is_admin: bool = False
    ) -> tuple[bool, str]:
        """Switch the current workspace (oid) for a user.

        Returns:
            (False, "user_not_found") if user does not exist.
            (False, "workspace_not_found") if workspace does not exist.
            (False, "not_associated") if user is not associated with the workspace (non-admin only).
            (True, "") on success.
        """
        user = session.get(UserModel, user_id)
        if not user:
            return False, "user_not_found"
        workspace = session.get(WorkSpaceModel, workspace_id)
        if not workspace:
            return False, "workspace_not_found"
        if not is_admin:
            relation = session.exec(
                select(WorkspaceUserModel).where(
                    WorkspaceUserModel.uid == user_id,
                    WorkspaceUserModel.oid == workspace_id,
                )
            ).first()
            if not relation:
                return False, "not_associated"
        user.oid = workspace_id
        session.add(user)
        session.commit()
        session.refresh(user)
        return True, ""
