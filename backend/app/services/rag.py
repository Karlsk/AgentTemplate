"""RAG service — orchestrates KB management, document ingestion, and search.

All operations are workspace-scoped.
Uses LlamaIndex for ingestion, vector storage, retrieval, and reranking.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, func, select

from app.core.common.config import settings
from app.core.common.crypt import base64_decrypt
from app.core.common.logging import TerraLogUtil
from app.core.rag.embedding.provider import (
    DEFAULT_SAFE_BATCH_SIZE,
    EmbeddingModelCapability,
    EmbeddingProviderRegistry,
    probe_embedding_dimension,
)
from app.core.rag.ingestion.parser import SUPPORTED_FILE_TYPES
from app.core.rag.ingestion.pipeline import run_ingestion
from app.core.rag.rerank.reranker import rerank_nodes
from app.core.rag.retrieval.retrievers import (
    hybrid_search,
    keyword_search,
    vector_search,
)
from app.core.rag.storage.vector_store import (
    add_nodes,
    delete_nodes_by_metadata,
    get_vector_store,
    query_nodes_by_doc_id,
)
from app.models.ai_model import AiModelDetail
from app.models.rag import DocumentModel, KnowledgeBaseModel
from app.schemas.rag import (
    ChunkPreviewItem,
    ChunkPreviewResponse,
    ChunkResult,
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


class RAGService:
    """Service for workspace-scoped RAG operations."""

    # ====================== Knowledge Base CRUD ======================

    @staticmethod
    async def create_knowledge_base(
        *,
        session: Session,
        workspace_id: int,
        info: KnowledgeBaseCreate,
    ) -> KnowledgeBaseResponse:
        """Create a new knowledge base."""
        existing = session.exec(
            select(KnowledgeBaseModel).where(
                KnowledgeBaseModel.workspace_id == workspace_id,
                KnowledgeBaseModel.name == info.name,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Knowledge base '{info.name}' already exists in this workspace",
            )

        if info.embedding_model_id:
            model = session.get(AiModelDetail, info.embedding_model_id)
            if not model or model.llm_type != "embedding":
                raise HTTPException(
                    status_code=400, detail="Invalid embedding model ID")

        kb = KnowledgeBaseModel(
            workspace_id=workspace_id,
            name=info.name,
            description=info.description,
            embedding_model_id=info.embedding_model_id,
            chunk_method=info.chunk_method,
            chunk_size=info.chunk_size,
            chunk_overlap=info.chunk_overlap,
            retrieval_mode=info.retrieval_mode,
            semantic_weight=info.semantic_weight,
            keyword_weight=info.keyword_weight,
            default_top_k=info.default_top_k,
            enable_score_threshold=info.enable_score_threshold,
            default_score_threshold=info.default_score_threshold,
            status=1,
        )
        session.add(kb)
        session.commit()
        session.refresh(kb)

        TerraLogUtil.info("knowledge_base_created",
                          kb_id=kb.id, workspace_id=workspace_id)
        return KnowledgeBaseResponse.model_validate(kb, from_attributes=True)

    @staticmethod
    async def update_knowledge_base(
        *,
        session: Session,
        workspace_id: int,
        info: KnowledgeBaseUpdate,
    ) -> KnowledgeBaseResponse:
        """Update an existing knowledge base."""
        kb = session.get(KnowledgeBaseModel, info.id)
        if not kb or kb.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        update_data = info.model_dump(exclude_unset=True, exclude={"id"})

        if "name" in update_data and update_data["name"] != kb.name:
            dup = session.exec(
                select(KnowledgeBaseModel).where(
                    KnowledgeBaseModel.workspace_id == workspace_id,
                    KnowledgeBaseModel.name == update_data["name"],
                )
            ).first()
            if dup:
                raise HTTPException(
                    status_code=400, detail="Name already taken")

        kb.sqlmodel_update(update_data)
        session.add(kb)
        session.commit()
        session.refresh(kb)
        TerraLogUtil.info("knowledge_base_updated", kb_id=kb.id)
        return KnowledgeBaseResponse.model_validate(kb, from_attributes=True)

    @staticmethod
    async def delete_knowledge_base(
        *,
        session: Session,
        workspace_id: int,
        kb_id: int,
    ) -> Dict[str, Any]:
        """Delete a KB, its documents, and all associated vector nodes."""
        kb = session.get(KnowledgeBaseModel, kb_id)
        if not kb or kb.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        # Remove vector nodes for this KB
        delete_nodes_by_metadata("kb_id", kb_id)

        # Remove documents & files
        docs = session.exec(select(DocumentModel).where(
            DocumentModel.kb_id == kb_id)).all()
        for doc in docs:
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except OSError:
                    pass
            session.delete(doc)

        session.delete(kb)
        session.commit()

        TerraLogUtil.info("knowledge_base_deleted",
                          kb_id=kb_id, doc_count=len(docs))
        return {"kb_id": kb_id, "deleted_documents": len(docs)}

    @staticmethod
    async def get_knowledge_base(
        *, session: Session, workspace_id: int, kb_id: int,
    ) -> KnowledgeBaseResponse:
        """Get a single KB."""
        kb = session.get(KnowledgeBaseModel, kb_id)
        if not kb or kb.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")
        return KnowledgeBaseResponse.model_validate(kb, from_attributes=True)

    @staticmethod
    async def list_knowledge_bases(
        *, session: Session, workspace_id: int, keyword: Optional[str] = None,
    ) -> List[KnowledgeBaseListItem]:
        """List KBs in a workspace."""
        stmt = select(KnowledgeBaseModel).where(
            KnowledgeBaseModel.workspace_id == workspace_id
        )
        if keyword:
            stmt = stmt.where(KnowledgeBaseModel.name.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(KnowledgeBaseModel.created_at.desc())

        kbs = session.exec(stmt).all()
        return [KnowledgeBaseListItem.model_validate(kb, from_attributes=True) for kb in kbs]

    # ====================== Document Management ======================

    @staticmethod
    async def upload_document(
        *,
        session: Session,
        workspace_id: int,
        kb_id: int,
        file: UploadFile,
        chunk_method: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        chunk_separator: Optional[str] = None,
    ) -> DocumentResponse:
        """Upload, ingest, and index a document."""
        kb = session.get(KnowledgeBaseModel, kb_id)
        if not kb or kb.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        filename = file.filename or "unknown"
        file_ext = filename.rsplit(
            ".", 1)[-1].lower() if "." in filename else ""
        if file_ext not in SUPPORTED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported: {', '.join(sorted(SUPPORTED_FILE_TYPES))}",
            )

        # Resolve effective chunking parameters (per-doc overrides KB defaults)
        effective_method = chunk_method or kb.chunk_method
        effective_size = chunk_size or kb.chunk_size
        effective_overlap = chunk_overlap or kb.chunk_overlap

        # Save to disk
        upload_dir = os.path.join(
            settings.RAG_UPLOAD_DIR, str(workspace_id), str(kb_id))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Create DB record with per-doc chunk params
        doc = DocumentModel(
            kb_id=kb_id,
            workspace_id=workspace_id,
            name=filename,
            file_path=file_path,
            file_type=file_ext,
            file_size=len(content),
            chunk_method=effective_method,
            chunk_size=effective_size,
            chunk_overlap=effective_overlap,
            chunk_separator=chunk_separator,
            status=1,  # processing
            processing_step="parsing",
            parse_progress=0,
            chunk_progress=0,
            embed_progress=0,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        try:
            cap = await _resolve_embed_capability(session, kb)

            # Build kwargs for chunking strategy
            chunk_kwargs = {}
            if chunk_separator:
                chunk_kwargs["separator"] = chunk_separator

            result = await run_ingestion(
                file_path=file_path,
                file_type=file_ext,
                embed_model=cap.model,
                doc_id=doc.id,
                kb_id=kb_id,
                workspace_id=workspace_id,
                chunk_method=effective_method,
                chunk_size=effective_size,
                chunk_overlap=effective_overlap,
                batch_size=cap.batch_size,
                session=session,
                doc_model=doc,
                **chunk_kwargs,
            )

            if result.nodes:
                add_nodes(result.nodes, embed_dim=cap.dimension)

            doc.chunk_count = result.chunk_count
            doc.status = 2  # completed
            doc.processing_step = "completed"
            doc.embed_progress = 100

            # Refresh KB counts
            kb.doc_count = session.exec(
                select(func.count(DocumentModel.id)).where(
                    DocumentModel.kb_id == kb_id)
            ).one()
            kb.chunk_count = (kb.chunk_count or 0) + result.chunk_count
            session.add(kb)

        except Exception as exc:
            doc.status = 3  # failed
            doc.error_msg = str(exc)
            TerraLogUtil.exception(
                "document_ingestion_failed", doc_id=doc.id, error=str(exc))

        session.add(doc)
        session.commit()
        session.refresh(doc)

        TerraLogUtil.info("document_uploaded", doc_id=doc.id,
                          chunk_count=doc.chunk_count)
        return DocumentResponse.model_validate(doc, from_attributes=True)

    @staticmethod
    async def delete_document(
        *, session: Session, workspace_id: int, kb_id: int, doc_id: int,
    ) -> Dict[str, Any]:
        """Delete a document and its vector nodes."""
        doc = session.get(DocumentModel, doc_id)
        if not doc or doc.kb_id != kb_id or doc.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Document not found")

        delete_nodes_by_metadata("source_doc_id", doc_id)

        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

        chunk_count = doc.chunk_count
        session.delete(doc)

        kb = session.get(KnowledgeBaseModel, kb_id)
        if kb:
            kb.doc_count = max(0, kb.doc_count - 1)
            kb.chunk_count = max(0, kb.chunk_count - chunk_count)
            session.add(kb)

        session.commit()
        TerraLogUtil.info("document_deleted", doc_id=doc_id,
                          chunk_count=chunk_count)
        return {"doc_id": doc_id, "deleted_chunks": chunk_count}

    @staticmethod
    async def list_documents(
        *, session: Session, workspace_id: int, kb_id: int,
    ) -> List[DocumentListItem]:
        """List documents in a KB."""
        kb = session.get(KnowledgeBaseModel, kb_id)
        if not kb or kb.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        docs = session.exec(
            select(DocumentModel)
            .where(DocumentModel.kb_id == kb_id, DocumentModel.workspace_id == workspace_id)
            .order_by(DocumentModel.created_at.desc())
        ).all()
        return [DocumentListItem.model_validate(d, from_attributes=True) for d in docs]

    # ====================== Document Progress & Preview ======================

    @staticmethod
    async def get_document_progress(
        *, session: Session, workspace_id: int, kb_id: int, doc_id: int,
    ) -> DocumentProgressResponse:
        """Get processing progress for a document."""
        doc = session.get(DocumentModel, doc_id)
        if not doc or doc.kb_id != kb_id or doc.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentProgressResponse(
            doc_id=doc.id,
            status=doc.status,
            processing_step=doc.processing_step,
            parse_progress=doc.parse_progress,
            chunk_progress=doc.chunk_progress,
            embed_progress=doc.embed_progress,
            error_msg=doc.error_msg,
        )

    @staticmethod
    async def get_document_chunks(
        *, session: Session, workspace_id: int, kb_id: int, doc_id: int,
        offset: int = 0, limit: int = 20,
    ) -> ChunkPreviewResponse:
        """Get paginated chunk preview for a completed document."""
        doc = session.get(DocumentModel, doc_id)
        if not doc or doc.kb_id != kb_id or doc.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc.status != 2:
            raise HTTPException(
                status_code=400, detail="Document processing not completed")

        chunks_data, total = query_nodes_by_doc_id(doc_id, offset, limit)
        chunks = [ChunkPreviewItem(**c) for c in chunks_data]

        return ChunkPreviewResponse(
            doc_id=doc.id,
            doc_name=doc.name,
            total_chunks=total,
            chunks=chunks,
        )

    # ====================== Search ======================

    @staticmethod
    async def search(
        *, session: Session, workspace_id: int, request: RAGSearchRequest,
    ) -> RAGSearchResponse:
        """Execute RAG retrieval across KBs."""
        start = time.perf_counter()

        # Validate KB ownership
        for kb_id in request.kb_ids:
            kb = session.get(KnowledgeBaseModel, kb_id)
            if not kb or kb.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=404, detail=f"KB {kb_id} not found")

        first_kb = session.get(KnowledgeBaseModel, request.kb_ids[0])
        cap = await _resolve_embed_capability(session, first_kb)

        # Ensure the vector store singleton is initialized with the
        # correct embedding dimension (critical after container restart)
        get_vector_store(embed_dim=cap.dimension)

        # Merge KB defaults with request overrides
        effective_mode = (
            request.search_mode or first_kb.retrieval_mode).lower()
        effective_top_k = request.top_k or first_kb.default_top_k

        if request.score_threshold is not None:
            effective_threshold = request.score_threshold
        elif first_kb.enable_score_threshold:
            effective_threshold = first_kb.default_score_threshold
        else:
            effective_threshold = 0.0

        effective_semantic_weight = request.semantic_weight or first_kb.semantic_weight
        effective_keyword_weight = request.keyword_weight or first_kb.keyword_weight

        # Retrieve
        if effective_mode == "vector":
            nodes = await vector_search(
                query=request.query,
                embed_model=cap.model,
                kb_ids=request.kb_ids,
                workspace_id=workspace_id,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
            )
        elif effective_mode == "keyword":
            nodes = await keyword_search(
                query=request.query,
                embed_model=cap.model,
                kb_ids=request.kb_ids,
                workspace_id=workspace_id,
                top_k=effective_top_k,
            )
        else:  # hybrid
            nodes = await hybrid_search(
                query=request.query,
                embed_model=cap.model,
                kb_ids=request.kb_ids,
                workspace_id=workspace_id,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
                vector_weight=effective_semantic_weight,
                keyword_weight=effective_keyword_weight,
            )

        # Optional rerank
        if request.rerank and nodes:
            nodes = await rerank_nodes(
                query=request.query,
                nodes=nodes,
                top_k=effective_top_k,
                model_name=settings.RAG_RERANK_MODEL,
            )

        # Build doc-name lookup
        doc_ids = list({
            n.node.metadata.get("source_doc_id")
            for n in nodes
            if n.node.metadata.get("source_doc_id")
        })
        doc_name_map: Dict[int, str] = {}
        if doc_ids:
            rows = session.exec(
                select(DocumentModel.id, DocumentModel.name).where(
                    DocumentModel.id.in_(doc_ids))
            ).all()
            doc_name_map = {r[0]: r[1] for r in rows}

        elapsed = round((time.perf_counter() - start) * 1000, 2)

        results = [
            ChunkResult(
                chunk_id=n.node.node_id,
                doc_id=n.node.metadata.get("source_doc_id"),
                kb_id=n.node.metadata.get("kb_id"),
                content=n.node.get_content(),
                score=round(n.score or 0.0, 4),
                metadata={
                    k: v for k, v in n.node.metadata.items()
                    if k not in ("source_doc_id", "kb_id", "workspace_id")
                } or None,
                doc_name=doc_name_map.get(
                    n.node.metadata.get("source_doc_id")),
            )
            for n in nodes
        ]

        TerraLogUtil.info(
            "rag_search_completed",
            result_count=len(results),
            search_mode=effective_mode,
            elapsed_ms=elapsed,
        )
        return RAGSearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            trace={
                "search_mode": effective_mode,
                "top_k": effective_top_k,
                "score_threshold": effective_threshold,
                "semantic_weight": effective_semantic_weight,
                "keyword_weight": effective_keyword_weight,
                "rerank": request.rerank,
                "elapsed_ms": elapsed,
            },
        )


# ====================== Internal helpers ======================

def _resolve_embed_model(session: Session, kb: KnowledgeBaseModel):
    """Resolve the LlamaIndex embedding model for a KB.

    Returns the cached EmbeddingModelCapability if available.
    Otherwise creates the model, but capability (dimension, batch_size)
    is populated lazily via ``_resolve_embed_capability`` after first probe.
    """
    model_id = kb.embedding_model_id

    if model_id:
        db_model = session.get(AiModelDetail, model_id)
    else:
        db_model = session.exec(
            select(AiModelDetail).where(
                AiModelDetail.llm_type == "embedding",
                AiModelDetail.status == 1,
            ).order_by(AiModelDetail.created_at.desc())
        ).first()

    if not db_model:
        raise HTTPException(
            status_code=500,
            detail="No embedding model configured. Add one in system settings.",
        )

    api_key = db_model.api_key or ""
    api_domain = db_model.api_domain or ""
    try:
        if api_domain and not api_domain.startswith("http"):
            api_domain = base64_decrypt(api_domain)
        if api_key and not api_key.startswith("sk-"):
            api_key = base64_decrypt(api_key)
    except Exception:
        pass

    # Parse model config for dimension and batch_size
    config_dimension = None
    config_batch_size = None
    if db_model.config:
        try:
            for item in json.loads(db_model.config):
                if item.get("key") == "dimension":
                    config_dimension = int(item["val"])
                elif item.get("key") == "batch_size":
                    config_batch_size = int(item["val"])
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Check if we already have cached capability for this model
    cached = EmbeddingProviderRegistry.get_capability(db_model.id)
    if cached:
        return cached

    embed_model = EmbeddingProviderRegistry.get(
        model_id=db_model.id,
        model_name=db_model.base_model,
        api_key=api_key,
        api_base=api_domain,
        dimension=config_dimension,
    )

    # Build a partial capability; dimension will be filled by probe if needed
    batch_size = config_batch_size or DEFAULT_SAFE_BATCH_SIZE
    dimension = config_dimension or settings.RAG_EMBEDDING_DIMENSION

    cap = EmbeddingModelCapability(
        model=embed_model,
        dimension=dimension,
        batch_size=batch_size,
    )

    return cap


async def _resolve_embed_capability(
    session: Session,
    kb: KnowledgeBaseModel,
) -> EmbeddingModelCapability:
    """Resolve embedding model capability, probing dimension if needed.

    On first call for a model, sends a test embedding to detect actual
    dimension and stores it back in model config for future use.
    """
    cap = _resolve_embed_model(session, kb)

    model_id = kb.embedding_model_id
    if model_id:
        db_model = session.get(AiModelDetail, model_id)
    else:
        db_model = session.exec(
            select(AiModelDetail).where(
                AiModelDetail.llm_type == "embedding",
                AiModelDetail.status == 1,
            ).order_by(AiModelDetail.created_at.desc())
        ).first()

    if not db_model:
        return cap

    # Check if dimension was already probed and cached
    cached = EmbeddingProviderRegistry.get_capability(db_model.id)
    if cached:
        return cached

    # Probe dimension dynamically
    try:
        probed_dim = await probe_embedding_dimension(cap.model)
        cap.dimension = probed_dim

        # Persist probed dimension back to model config
        _save_model_config(session, db_model, "dimension", probed_dim)

        TerraLogUtil.info(
            "embedding_capability_detected",
            model_id=db_model.id,
            dimension=probed_dim,
            batch_size=cap.batch_size,
        )
    except Exception:
        TerraLogUtil.warning(
            "embedding_probe_fallback",
            model_id=db_model.id,
            dimension=cap.dimension,
        )

    EmbeddingProviderRegistry.set_capability(db_model.id, cap)
    return cap


def _save_model_config(
    session: Session,
    db_model: AiModelDetail,
    key: str,
    value: Any,
) -> None:
    """Upsert a key/value pair in the model's JSON config array."""
    config_list = []
    if db_model.config:
        try:
            config_list = json.loads(db_model.config)
        except (json.JSONDecodeError, ValueError):
            config_list = []

    # Update existing or append new
    found = False
    for item in config_list:
        if item.get("key") == key:
            item["val"] = value
            found = True
            break
    if not found:
        config_list.append({"key": key, "val": value, "name": key})

    db_model.config = json.dumps(config_list)
    session.add(db_model)
    session.commit()
