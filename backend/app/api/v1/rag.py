"""RAG API endpoints for managing RAG instances and vector search."""

import json
import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.common.deps import CurrentUser, SessionDep
from app.core.common.limiter import limiter
from app.core.common.config import settings
from app.services.rag import RagService
from app.models.rag import RagInstanceModel
from pydantic import BaseModel

router = APIRouter()
rag_service = RagService()

def _get_workspace_id(current_user: object) -> int:
    if hasattr(current_user, "oid"):
        return int(getattr(current_user, "oid"))
    if isinstance(current_user, dict) and "oid" in current_user:
        return int(current_user["oid"])
    raise HTTPException(status_code=401, detail="workspace_id_missing")


class RagInstanceCreate(BaseModel):
    name: str
    embedding_model_id: int
    dimension: int
    config: Optional[dict] = None


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: Optional[dict] = None


@router.post("/instance", response_model=RagInstanceModel)
@limiter.limit("10 per minute")
async def create_rag_instance(
    request: Request,
    data: RagInstanceCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Create a new RAG instance."""
    try:
        workspace_id = _get_workspace_id(current_user)
        instance = await rag_service.create_instance(
            workspace_id=workspace_id,
            name=data.name,
            embedding_model_id=data.embedding_model_id,
            dimension=data.dimension,
            config=data.config
        )
        return instance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instance", response_model=List[RagInstanceModel])
@limiter.limit("30 per minute")
async def list_rag_instances(
    request: Request,
    current_user: CurrentUser,
):
    """List RAG instances for the current workspace."""
    workspace_id = _get_workspace_id(current_user)
    return await rag_service.list_instances(workspace_id=workspace_id)


@router.get("/instance/{instance_id}", response_model=RagInstanceModel)
@limiter.limit("60 per minute")
async def get_rag_instance(
    request: Request,
    instance_id: int,
    current_user: CurrentUser,
):
    """Get a RAG instance."""
    workspace_id = _get_workspace_id(current_user)
    instance = await rag_service.get_instance(workspace_id=workspace_id, instance_id=instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="RAG instance not found")
    return instance


@router.delete("/instance/{instance_id}")
@limiter.limit("20 per minute")
async def delete_rag_instance(
    request: Request,
    instance_id: int,
    current_user: CurrentUser,
):
    """Delete a RAG instance."""
    workspace_id = _get_workspace_id(current_user)
    success = await rag_service.delete_instance(workspace_id=workspace_id, instance_id=instance_id)
    if not success:
        raise HTTPException(status_code=404, detail="RAG instance not found")
    return {"message": "RAG instance deleted successfully"}


@router.post("/instance/{instance_id}/upload")
@limiter.limit("10 per minute")
async def upload_document(
    request: Request,
    instance_id: int,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    cleaner: str = Form("basic"),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(64),
):
    """Upload and process a document."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        workspace_id = _get_workspace_id(current_user)
        await rag_service.process_file(
            workspace_id=workspace_id,
            instance_id=instance_id,
            file_path=tmp_path,
            filename=file.filename,
            cleaner=cleaner,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return {"message": "file_processed_successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

class RagChatRequest(BaseModel):
    query: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    llm_model: Optional[str] = None


class RagPreviewItem(BaseModel):
    id: str
    document_id: Optional[str] = None
    index: Optional[int] = None
    metadata: dict
    content: str
    truncated: bool


class RagPreviewResponse(BaseModel):
    documents: List[RagPreviewItem]
    raw_chunks: List[RagPreviewItem]
    clean_chunks: List[RagPreviewItem]
    counts: dict
    options: dict


@router.post("/instance/{instance_id}/search")
@limiter.limit("60 per minute")
async def search_rag_instance(
    request: Request,
    instance_id: int,
    data: RagSearchRequest,
    current_user: CurrentUser,
):
    """Search in a RAG instance."""
    try:
        workspace_id = _get_workspace_id(current_user)
        results = await rag_service.search(
            workspace_id=workspace_id,
            instance_id=instance_id,
            query=data.query,
            top_k=data.top_k
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instance/{instance_id}/chat")
@limiter.limit("20 per minute")
async def chat_rag_instance(
    request: Request,
    instance_id: int,
    data: RagChatRequest,
    current_user: CurrentUser,
):
    """Chat with a RAG instance."""
    try:
        workspace_id = _get_workspace_id(current_user)
        async def event_generator():
            try:
                async for chunk in rag_service.chat(
                    workspace_id=workspace_id,
                    instance_id=instance_id,
                    query=data.query,
                    system_prompt=data.system_prompt,
                    temperature=data.temperature,
                    max_tokens=data.max_tokens,
                    llm_model=data.llm_model
                ):
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instance/{instance_id}/preview", response_model=RagPreviewResponse)
@limiter.limit("10 per minute")
async def preview_document(
    request: Request,
    instance_id: int,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    cleaner: str = Form("basic"),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(64),
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        workspace_id = _get_workspace_id(current_user)
        data = await rag_service.preview_file(
            workspace_id=workspace_id,
            instance_id=instance_id,
            file_path=tmp_path,
            filename=file.filename,
            cleaner=cleaner,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
