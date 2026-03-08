import json

from pydantic.types import T
from sqlmodel import Session, func, select, update
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.models.ai_model import AiModelDetail
from app.models.user import UserModel
from app.schemas.ai_model import AiModelCreator, AiModelEditor, AiModelConfigItem, AiModelGridItem, AiModelItem
from app.core.common.crypt import base64_decrypt, base64_encrypt


class SystemService:

    @staticmethod
    async def get_default_llm_config(*, session: Session):
        db_model = session.exec(
            select(AiModelDetail).where(AiModelDetail.default_model == True)
        ).first()
        if not db_model:
            raise HTTPException(
                status_code=404, detail="No default LLM model found")
        return db_model

    @staticmethod
    async def get_backup_llm_config(*, session: Session):
        db_model = session.exec(
            select(AiModelDetail).where(AiModelDetail.backup_model == True)
        ).first()
        if not db_model:
            raise HTTPException(
                status_code=404, detail="No backup LLM model found")
        return db_model

    @staticmethod
    async def create_ai_model(*, session: Session, info: AiModelCreator, current_user: UserModel):
        data = info.model_dump(exclude_unset=True)
        data["config"] = json.dumps(
            [item.model_dump(exclude_unset=True) for item in info.config_list])
        data.pop("config_list", None)
        detail = AiModelDetail.model_validate(data)

        count = session.exec(select(func.count(AiModelDetail.id))).one()
        if count == 0:
            detail.default_model = True
        session.add(detail)
        session.commit()
        session.refresh(detail)
        return detail

    @staticmethod
    async def update_ai_model(*, session: Session, editor: AiModelEditor, current_user: UserModel):
        id = int(editor.id)
        data = editor.model_dump(exclude_unset=True)
        data["config"] = json.dumps(
            [item.model_dump(exclude_unset=True) for item in editor.config_list])
        data.pop("config_list", None)
        db_model = session.get(AiModelDetail, id)
        # update_data = AiModelDetail.model_validate(data)
        db_model.sqlmodel_update(data)
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return db_model

    @staticmethod
    async def delete_ai_model(*, session: Session, id: int, current_user: UserModel):
        item = session.get(AiModelDetail, id)
        if not item:
            return JSONResponse(content={"id": id, "message": "AI model not found"}, status_code=404)
        if item.default_model or item.backup_model:
            return JSONResponse(content={"id": id, "message": "Cannot delete default or backup AI model"}, status_code=400)
        session.commit()
        return JSONResponse(content={"id": id, "message": "AI model deleted successfully"}, status_code=200)

    @staticmethod
    async def set_default_llm(*, session: Session, id: int, current_user: UserModel):
        db_model = session.get(AiModelDetail, id)
        if not db_model:
            return JSONResponse(content={"id": id, "message": "AI model not found"}, status_code=404)
        if db_model.default_model:
            return JSONResponse(content={"id": id, "message": "AI model is already the default model"}, status_code=200)

        try:
            session.exec(
                update(AiModelDetail).values(default_model=False)
            )
            db_model.default_model = True
            session.add(db_model)
            session.commit()
            return JSONResponse(content={"id": id, "message": "AI model set as default successfully"}, status_code=200)
        except Exception as e:
            session.rollback()
            return JSONResponse(content={"id": id, "message": "Failed to set AI model as default"}, status_code=500)

    @staticmethod
    async def set_backup_llm(*, session: Session, id: int, current_user: UserModel):
        db_model = session.get(AiModelDetail, id)
        if not db_model:
            return JSONResponse(content={"id": id, "message": "AI model not found"}, status_code=404)
        if db_model.backup_model:
            return JSONResponse(content={"id": id, "message": "AI model is already the backup model"}, status_code=200)

        try:
            session.exec(
                update(AiModelDetail).values(backup_model=False)
            )
            db_model.backup_model = True
            session.add(db_model)
            session.commit()
            return JSONResponse(content={"id": id, "message": "AI model set as backup successfully"}, status_code=200)
        except Exception as e:
            session.rollback()
            return JSONResponse(content={"id": id, "message": "Failed to set AI model as backup"}, status_code=500)

    @staticmethod
    async def get_ai_model_list(*, session: Session, keyword: str):
        statement = select(
            AiModelDetail.id,
            AiModelDetail.name,
            AiModelDetail.base_model,
            AiModelDetail.supplier,
            AiModelDetail.protocol,
            AiModelDetail.default_model,
            AiModelDetail.llm_type,
            AiModelDetail.backup_model
        )
        if keyword is not None:
            statement = statement.where(
                AiModelDetail.name.like(f"%{keyword}%"))
        statement = statement.order_by(AiModelDetail.default_model.desc(
        ), AiModelDetail.name, AiModelDetail.created_at)
        items = session.exec(statement).all()
        # Convert tuples to dictionaries
        return [
            {
                "id": item[0],
                "name": item[1],
                "base_model": item[2],
                "supplier": item[3],
                "protocol": item[4],
                "default_model": item[5],
                "llm_type": item[6],
                "backup_model": item[7]
            }
            for item in items
        ]

    @staticmethod
    async def get_model_by_id(*, session: Session, id: int):
        db_model = session.get(AiModelDetail, id)
        if not db_model:
            raise ValueError(f"AiModelDetail with id {id} not found")

        config_list: List[AiModelConfigItem] = []
        if db_model.config:
            try:
                raw = json.loads(db_model.config)
                config_list = [AiModelConfigItem(**item) for item in raw]
            except Exception:
                pass
        try:
            if db_model.api_key:
                db_model.api_key = base64_decrypt(db_model.api_key)
            if db_model.api_domain:
                db_model.api_domain = base64_decrypt(db_model.api_domain)
        except Exception:
            pass
        data = AiModelDetail.model_validate(
            db_model).model_dump(exclude_unset=True)
        data.pop("config", None)
        data["config_list"] = config_list
        return AiModelEditor(**data)
