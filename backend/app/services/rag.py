"""RAG Service for managing RAG instances and their vector collections."""

import json
import os
import shutil
import tempfile
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, select

from app.core.common.db import engine
from app.core.common.logging import TerraLogUtil as logger
from app.core.llm.embedding import EmbeddingFactory, EmbeddingConfig
from app.core.llm.model_factory import LLMFactory, get_default_config
from app.core.common.crypt import base64_decrypt
from app.core.rag.loader import get_loader
from app.core.rag.splitter.recursive import RecursiveSplitter
from app.core.rag.store import get_vector_store
from app.models.ai_model import AiModelDetail
from app.models.rag import RagInstanceModel
from app.utils.sanitization import prepare_model_arg


class RagService:
    """Service for managing RAG instances and collections."""

    def __init__(self):
        self.vector_store = get_vector_store()

    async def chat(
        self, 
        workspace_id: int, 
        instance_id: int, 
        query: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        llm_model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Chat with a RAG instance using retrieved context."""
        instance = await self.get_instance(workspace_id, instance_id)
        if not instance:
            raise ValueError("Instance not found")

        # 1. Retrieve context
        results = await self.search(workspace_id, instance_id, query, top_k=5)
        context = "\n\n".join([f"--- Context {i + 1} ---\n{r.chunk.content}" for i, r in enumerate(results)])

        # 2. Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        prompt = f"Answer the following question based on the provided context.\n\nContext:\n{context}\n\nQuestion: {query}"

        llm_config = await get_default_config()
        if llm_model:
            llm_config = llm_config.model_copy(update={"model_name": llm_model})
        llm = LLMFactory.create_llm(llm_config).llm

        lc_messages: list[Any] = []
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))
        lc_messages.append(HumanMessage(content=prompt))

        async for chunk in llm.astream(
            lc_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            content = getattr(chunk, "content", "") or ""
            if content:
                yield content

    async def _get_embedding_model(self, model_id: int) -> Any:
        """Get an embedding model instance for the given model ID."""
        with Session(engine) as session:
            db_model = session.get(AiModelDetail, model_id)
            if not db_model:
                raise ValueError("embedding_model_not_found")

            additional_params = {}
            if db_model.config:
                try:
                    config_raw = json.loads(db_model.config)
                    additional_params = {
                        item["key"]: prepare_model_arg(item.get('val')) 
                        for item in config_raw if "key" in item and "val" in item
                    }
                except Exception:
                    pass
            
            api_domain = db_model.api_domain or ""
            api_key = db_model.api_key
            if api_domain and not api_domain.startswith("http"):
                try:
                    api_domain = base64_decrypt(api_domain)
                except Exception:
                    api_domain = ""
            if api_key:
                try:
                    api_key = base64_decrypt(api_key)
                except Exception:
                    api_key = db_model.api_key

            # Get dimensions from config or default
            dimensions = additional_params.get("dimensions", 1536)
            
            config = EmbeddingConfig(
                model_name=db_model.base_model,
                dimensions=dimensions,
                api_key=api_key,
                api_base=api_domain,
                additional_params=additional_params
            )
            return EmbeddingFactory.get_embedding(config)

    async def process_file(
        self,
        workspace_id: int,
        instance_id: int,
        file_path: str,
        filename: str,
        cleaner: str = "basic",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ):
        """Process a file: load, clean, split, embed, and insert into vector store."""
        instance = await self.get_instance(workspace_id, instance_id)
        if not instance:
            raise ValueError("rag_instance_not_found")

        logger.info(
            "rag_file_processing_started",
            instance_id=instance_id,
            workspace_id=workspace_id,
            filename=filename,
            cleaner=cleaner,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        try:
            loader = get_loader(filename)
            documents = loader.load(file_path)
            logger.info(
                "rag_file_loaded",
                instance_id=instance_id,
                workspace_id=workspace_id,
                filename=filename,
                doc_count=len(documents),
            )

            splitter = RecursiveSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = []
            for doc in documents:
                chunks.extend(splitter.split(doc))

            if cleaner and cleaner != "none":
                for c in chunks:
                    if cleaner == "basic":
                        c.content = re.sub(r"\s+", " ", c.content).strip()
                    elif cleaner == "strip":
                        c.content = c.content.strip()

            chunks = [c for c in chunks if c.content]
            logger.info(
                "rag_file_split",
                instance_id=instance_id,
                workspace_id=workspace_id,
                chunk_count=len(chunks),
            )

            if not chunks:
                logger.info(
                    "rag_file_no_chunks",
                    instance_id=instance_id,
                    workspace_id=workspace_id,
                    filename=filename,
                )
                return

            embedding_model = await self._get_embedding_model(instance.embedding_model_id)
            texts = [chunk.content for chunk in chunks]
            embeddings = embedding_model.embed(texts)
            if len(embeddings) != len(chunks):
                raise ValueError("embedding_count_mismatch")

            for chunk, emb in zip(chunks, embeddings):
                chunk.embedding = emb

            dimension = len(embeddings[0]) if embeddings else 1536
            self.vector_store.create_collection(
                name=instance.collection_name,
                dimension=dimension,
            )
            self.vector_store.insert(instance.collection_name, chunks)

            logger.info(
                "rag_file_processed",
                instance_id=instance_id,
                workspace_id=workspace_id,
                filename=filename,
                chunk_count=len(chunks),
            )
        except Exception:
            logger.exception(
                "rag_file_processing_failed",
                instance_id=instance_id,
                workspace_id=workspace_id,
                filename=filename,
            )
            raise

    async def preview_file(
        self,
        workspace_id: int,
        instance_id: int,
        file_path: str,
        filename: str,
        cleaner: str = "basic",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        max_docs: int = 3,
        max_doc_chars: int = 6000,
        max_chunks: int = 50,
        max_chunk_chars: int = 1200,
    ) -> dict[str, Any]:
        instance = await self.get_instance(workspace_id, instance_id)
        if not instance:
            raise ValueError("rag_instance_not_found")

        loader = get_loader(filename)
        documents = loader.load(file_path)

        doc_previews: list[dict[str, Any]] = []
        for d in documents[:max_docs]:
            content = d.content or ""
            doc_previews.append(
                {
                    "id": d.id,
                    "metadata": d.metadata.model_dump(),
                    "content": content[:max_doc_chars],
                    "truncated": len(content) > max_doc_chars,
                }
            )

        splitter = RecursiveSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks_raw = []
        for doc in documents:
            chunks_raw.extend(splitter.split(doc))

        raw_items: list[dict[str, Any]] = []
        clean_items: list[dict[str, Any]] = []

        for c in chunks_raw[:max_chunks]:
            raw_content = c.content or ""
            clean_content = raw_content
            if cleaner and cleaner != "none":
                if cleaner == "basic":
                    clean_content = re.sub(r"\s+", " ", raw_content).strip()
                elif cleaner == "strip":
                    clean_content = raw_content.strip()

            raw_items.append(
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "index": c.index,
                    "metadata": c.metadata.model_dump(),
                    "content": raw_content[:max_chunk_chars],
                    "truncated": len(raw_content) > max_chunk_chars,
                }
            )
            clean_items.append(
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "index": c.index,
                    "metadata": c.metadata.model_dump(),
                    "content": clean_content[:max_chunk_chars],
                    "truncated": len(clean_content) > max_chunk_chars,
                }
            )

        return {
            "documents": doc_previews,
            "raw_chunks": raw_items,
            "clean_chunks": clean_items,
            "counts": {
                "documents": len(documents),
                "chunks": len(chunks_raw),
            },
            "options": {
                "cleaner": cleaner,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        }

    async def search(self, workspace_id: int, instance_id: int, query: str, top_k: int = 5) -> List[Any]:
        """Search in a RAG instance."""
        instance = await self.get_instance(workspace_id, instance_id)
        if not instance:
            raise ValueError("Instance not found")

        embedding_model = await self._get_embedding_model(instance.embedding_model_id)
        query_vector = embedding_model.embed_query(query)
        
        return self.vector_store.search(instance.collection_name, query_vector, top_k=top_k)

    async def create_instance(
        self, 
        workspace_id: int, 
        name: str, 
        embedding_model_id: int,
        dimension: int,
        config: Optional[Dict[str, Any]] = None
    ) -> RagInstanceModel:
        """Create a new RAG instance and its corresponding vector collection."""
        with Session(engine) as session:
            # 1. Create the database record first to get the ID
            merged_config = dict(config or {})
            merged_config.setdefault("dimension", dimension)
            instance = RagInstanceModel(
                workspace_id=workspace_id,
                name=name,
                collection_name="temp",  # Placeholder
                embedding_model_id=embedding_model_id,
                config=json.dumps(merged_config) if merged_config else None
            )
            session.add(instance)
            session.commit()
            session.refresh(instance)

            # 2. Update the collection name based on the ID
            instance.collection_name = f"instance_{instance.id}"
            session.add(instance)
            session.commit()
            session.refresh(instance)

            # 3. Create the vector collection
            try:
                self.vector_store.create_collection(
                    name=instance.collection_name,
                    dimension=dimension,
                    description=f"Collection for RAG instance {instance.id} (Workspace {workspace_id})"
                )
                logger.info("created_rag_collection", collection=instance.collection_name, instance_id=instance.id)
            except Exception as e:
                logger.exception("failed_to_create_rag_collection", collection=instance.collection_name)
                # Rollback DB record if collection creation fails
                session.delete(instance)
                session.commit()
                raise e

            return instance

    async def get_instance(self, workspace_id: int, instance_id: int) -> Optional[RagInstanceModel]:
        """Get a RAG instance with workspace isolation."""
        with Session(engine) as session:
            statement = select(RagInstanceModel).where(
                RagInstanceModel.id == instance_id,
                RagInstanceModel.workspace_id == workspace_id
            )
            return session.exec(statement).first()

    async def list_instances(self, workspace_id: int) -> List[RagInstanceModel]:
        """List all RAG instances for a workspace."""
        with Session(engine) as session:
            statement = select(RagInstanceModel).where(
                RagInstanceModel.workspace_id == workspace_id
            )
            return list(session.exec(statement).all())

    async def delete_instance(self, workspace_id: int, instance_id: int) -> bool:
        """Delete a RAG instance and its Milvus collection."""
        with Session(engine) as session:
            instance = await self.get_instance(workspace_id, instance_id)
            if not instance:
                return False

            # 1. Drop Milvus collection
            try:
                self.vector_store.drop_collection(instance.collection_name)
                logger.info("dropped_rag_collection", collection=instance.collection_name)
            except Exception as e:
                logger.warning("failed_to_drop_rag_collection", collection=instance.collection_name, error=str(e))
                # Continue even if collection drop fails (e.g. if it didn't exist)

            # 2. Delete DB record
            session.delete(instance)
            session.commit()
            return True

    async def update_instance(
        self, 
        workspace_id: int, 
        instance_id: int, 
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[RagInstanceModel]:
        """Update a RAG instance with workspace isolation."""
        with Session(engine) as session:
            instance = await self.get_instance(workspace_id, instance_id)
            if not instance:
                return None

            if name:
                instance.name = name
            if config:
                instance.config = json.dumps(config)

            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
