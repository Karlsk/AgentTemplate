from __future__ import annotations

from app.core.llm.embedding import BaseEmbedding
from app.core.rag.models.search import ScoredDocument
from app.core.rag.retrieval.base import BaseRetriever
from app.core.rag.store.base import BaseVectorStore


class VectorRetriever(BaseRetriever):
    """Retrieve documents using vector similarity search."""

    def __init__(self, store: BaseVectorStore, embedding: BaseEmbedding, collection: str):
        self._store = store
        self._embedding = embedding
        self._collection = collection

    async def retrieve(self, query: str, top_k: int = 10, **kwargs) -> list[ScoredDocument]:
        query_vector = await self._embedding.embed_query(query)
        results = self._store.search(
            collection=self._collection,
            query_vector=query_vector,
            top_k=top_k,
            filters=kwargs.get("filters"),
        )
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
