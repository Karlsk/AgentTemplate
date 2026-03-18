"""RAG API routes — knowledge base management, document upload, and search.

All endpoints are workspace-scoped via the current user's ``oid``.
"""

from typing import List, Optional, Union

from fastapi import APIRouter, File, Form, Path, Query, Request, UploadFile

from app.core.common.deps import CurrentUser, SessionDep
from app.core.common.limiter import limiter
from app.schemas.rag import (
    ChunkPreviewResponse,
    DocumentListItem,
    DocumentProgressResponse,
    DocumentResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseListItem,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    RAGSearchRequest,
    RAGSearchResponse,
)
from app.services.rag import RAGService


router = APIRouter(tags=["rag"], prefix="/rag")
rag_service = RAGService()


# ==================== Knowledge Base ====================


@router.post(
    "/kb",
    response_model=KnowledgeBaseResponse,
    summary="create_knowledge_base",
)
@limiter.limit("30/minute")
async def create_knowledge_base(
    request: Request,
    info: KnowledgeBaseCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Create a new knowledge base in the current workspace."""
    return await rag_service.create_knowledge_base(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.put(
    "/kb",
    response_model=KnowledgeBaseResponse,
    summary="update_knowledge_base",
)
@limiter.limit("30/minute")
async def update_knowledge_base(
    request: Request,
    info: KnowledgeBaseUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Update an existing knowledge base."""
    return await rag_service.update_knowledge_base(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.delete("/kb/{kb_id}", summary="delete_knowledge_base")
@limiter.limit("10/minute")
async def delete_knowledge_base(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
):
    """Delete a knowledge base and all associated data."""
    return await rag_service.delete_knowledge_base(
        session=session, workspace_id=_ws(current_user), kb_id=kb_id,
    )


@router.get(
    "/kb/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="get_knowledge_base",
)
@limiter.limit("50/minute")
async def get_knowledge_base(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
):
    """Get a single knowledge base by ID."""
    return await rag_service.get_knowledge_base(
        session=session, workspace_id=_ws(current_user), kb_id=kb_id,
    )


@router.get(
    "/kb",
    response_model=List[KnowledgeBaseListItem],
    summary="list_knowledge_bases",
)
@limiter.limit("50/minute")
async def list_knowledge_bases(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    keyword: Union[str, None] = Query(default=None, max_length=255),
):
    """List knowledge bases in the current workspace."""
    return await rag_service.list_knowledge_bases(
        session=session, workspace_id=_ws(current_user), keyword=keyword,
    )


# ==================== Documents ====================


@router.post(
    "/kb/{kb_id}/documents",
    response_model=DocumentResponse,
    summary="upload_document",
)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
    file: UploadFile = File(...),
    chunk_method: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    chunk_separator: Optional[str] = Form(None),
):
    """Upload and ingest a document into a knowledge base."""
    return await rag_service.upload_document(
        session=session,
        workspace_id=_ws(current_user),
        kb_id=kb_id,
        file=file,
        chunk_method=chunk_method,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_separator=chunk_separator,
    )


@router.delete(
    "/kb/{kb_id}/documents/{doc_id}",
    summary="delete_document",
)
@limiter.limit("10/minute")
async def delete_document(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
    doc_id: int = Path(...),
):
    """Delete a document and its chunks."""
    return await rag_service.delete_document(
        session=session, workspace_id=_ws(current_user), kb_id=kb_id, doc_id=doc_id,
    )


@router.get(
    "/kb/{kb_id}/documents",
    response_model=List[DocumentListItem],
    summary="list_documents",
)
@limiter.limit("50/minute")
async def list_documents(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
):
    """List documents in a knowledge base."""
    return await rag_service.list_documents(
        session=session, workspace_id=_ws(current_user), kb_id=kb_id,
    )


@router.get(
    "/kb/{kb_id}/documents/{doc_id}/progress",
    response_model=DocumentProgressResponse,
    summary="get_document_progress",
)
@limiter.limit("50/minute")
async def get_document_progress(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
    doc_id: int = Path(...),
):
    """Get document processing progress."""
    return await rag_service.get_document_progress(
        session=session, workspace_id=_ws(current_user), kb_id=kb_id, doc_id=doc_id,
    )


@router.get(
    "/kb/{kb_id}/documents/{doc_id}/chunks",
    response_model=ChunkPreviewResponse,
    summary="get_document_chunks",
)
@limiter.limit("30/minute")
async def get_document_chunks(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    kb_id: int = Path(...),
    doc_id: int = Path(...),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get paginated chunk preview for a processed document."""
    return await rag_service.get_document_chunks(
        session=session, workspace_id=_ws(current_user),
        kb_id=kb_id, doc_id=doc_id, offset=offset, limit=limit,
    )


# ==================== Search ====================


@router.post(
    "/search",
    response_model=RAGSearchResponse,
    summary="rag_search",
)
@limiter.limit("30/minute")
async def rag_search(
    request: Request,
    body: RAGSearchRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Search knowledge bases (vector / keyword / hybrid)."""
    return await rag_service.search(
        session=session, workspace_id=_ws(current_user), request=body,
    )


# ==================== Helpers ====================

def _ws(user) -> int:
    """Extract workspace_id from current_user."""
    if isinstance(user, dict):
        return user.get("oid", 1)
    return getattr(user, "oid", 1)
