import json
from typing import List, Union

from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter, Path, Query, Request
from sqlmodel import func, select, update

from app.core.common.permissions import require_permissions
from app.schemas.ai_model import AiModelCreator, AiModelEditor, AiModelGridItem
from app.services.system import SystemService

from app.core.common.deps import CurrentUser, SessionDep
from app.core.llm.model_factory import LLMConfig, LLMFactory
from app.core.common.logging import TerraLogUtil
from app.utils.sanitization import prepare_model_arg
from app.core.common.crypt import base64_encrypt


router = APIRouter(tags=["system_aimodel"], prefix="/system/aimodel")
system_service = SystemService()


@router.post("/status")
@require_permissions(roles=['admin'])
async def check_llm(
    info: AiModelCreator,
    request: Request,
    current_user: CurrentUser
):
    async def generate():
        try:
            additional_params = {item.key: prepare_model_arg(
                item.val) for item in info.config_list if item.key and item.val}
            config = LLMConfig(
                model_type="openai" if info.protocol == 1 else "vllm",
                model_name=info.base_model,
                api_key=info.api_key,
                api_base_url=info.api_domain,
                additional_params=additional_params,
            )
            llm_instance = LLMFactory.create_llm(config)
            async for chunk in llm_instance.llm.astream("1+1=?"):
                TerraLogUtil.info(chunk)
                if chunk and isinstance(chunk, str):
                    yield json.dumps({"content": chunk}) + "\n"
                if chunk and isinstance(chunk, dict) and chunk.content:
                    yield json.dumps({"content": chunk.content}) + "\n"
        except Exception as e:
            TerraLogUtil.error(f"Error checking LLM: {e}", exc_info=True)
            error_msg = str(e)
            yield json.dumps({"error": error_msg}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.get("/default")
@require_permissions(roles=['admin'])
async def get_default_llm_config(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep
):
    model = await system_service.get_default_llm_config(session)
    return model


@router.get("/backup")
@require_permissions(roles=['admin'])
async def get_backup_llm_config(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep
):
    model = await system_service.get_backup_llm_config(session)
    return model


@router.put("/default/{id}", summary=f"set_model_default", description=f"set_model_default")
@require_permissions(roles=['admin'])
async def set_default_llm(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    id: int = Path(..., title="The ID of the ai model to set as default"),
):
    info = await system_service.set_default_llm(id=id, current_user=current_user, session=session)
    return info


@router.put("/backup/{id}", summary=f"set_model_backup", description=f"set_model_backup")
@require_permissions(roles=['admin'])
async def set_backup_llm(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    id: int = Path(..., title="The ID of the ai model to set as backup"),
):
    info = await system_service.set_backup_llm(id=id, current_user=current_user, session=session)
    return info


@router.post("", summary=f"ai_model_create", description=f"ai_model_create")
@require_permissions(roles=['admin'])
async def create_ai_model(
    request: Request,
    info: AiModelCreator,
    current_user: CurrentUser,
    session: SessionDep
):
    models = await system_service.create_ai_model(
        info=info, current_user=current_user, session=session)
    return models


@router.put("", summary=f"ai_model_update", description=f"ai_model_update")
@require_permissions(roles=['admin'])
async def update_ai_model(
    request: Request,
    info: AiModelEditor,
    current_user: CurrentUser,
    session: SessionDep
):
    models = await system_service.update_ai_model(
        editor=info, current_user=current_user, session=session)
    return models


@router.delete("/{id}", summary=f"ai_model_del", description=f"ai_model_del")
@require_permissions(roles=['admin'])
async def delete_ai_model(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    id: int = Path(..., title="The ID of the ai model to delete"),
):
    info = await system_service.delete_ai_model(id=id, current_user=current_user, session=session)
    return info


@router.get("", response_model=List[AiModelGridItem], summary=f"ai_model_list", description=f"ai_model_list")
@require_permissions(roles=['admin'])
async def get_ai_model_list(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    keyword: Union[str, None] = Query(
        default=None, max_length=255, description=f"keyword")
):
    models = await system_service.get_ai_model_list(session=session, keyword=keyword)
    # Convert SQLModel objects to Pydantic models for proper serialization
    return [AiModelGridItem.model_validate(model) for model in models]


@router.get("/{id}", response_model=AiModelEditor, summary=f"ai_model_query", description=f"ai_model_query")
@require_permissions(roles=['admin'])
async def get_model_by_id(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    id: int = Path(..., title="The ID of the ai model to query"),
):
    model = await system_service.get_model_by_id(id=id, session=session)
    # Encrypt api_key in response if present
    if model.api_key:
        model.api_key = base64_encrypt(model.api_key)
    return model
