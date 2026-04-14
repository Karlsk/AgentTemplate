from __future__ import annotations

from typing import Any

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil as logger
from app.core.llm.embedding import EmbeddingFactory, EmbeddingConfig
from app.core.rag.pipeline.base import ComponentBase, ComponentParam
from app.core.rag.pipeline.registry import register_component, register_param
from app.core.rag.retrieval.vector import VectorRetriever
from app.core.rag.store import get_vector_store



class RetrievalParam(ComponentParam):
    def __init__(self) -> None:
        super().__init__()
        self.collection: str = ""
        self.top_k: int = 5

    def check(self) -> None:
        if not self.collection:
            raise ValueError("Retrieval component requires a collection name")


register_param("Retrieval")(RetrievalParam)


@register_component("Retrieval")
class RetrievalComponent(ComponentBase):
    """Retrieve relevant chunks from a vector store."""

    component_name = "Retrieval"

    async def invoke(self, **kwargs: Any) -> dict[str, Any]:
        param: RetrievalParam = self._param  # type: ignore[assignment]

        query = self._context.get_global("sys.query", "")

        try:
            store = get_vector_store()
            emb_config = EmbeddingConfig(
                model_name=getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small"),
                dimensions=1536,
                api_key=getattr(settings, "OPENAI_API_KEY", "") or "Empty",
                api_base=getattr(settings, "OPENAI_BASE_URL", None),
            )
            embedding = EmbeddingFactory.get_embedding(emb_config)
            retriever = VectorRetriever(store=store, embedding=embedding, collection=param.collection)

            results = await retriever.retrieve(query, top_k=param.top_k)
            chunks_text = "\n\n".join(r.chunk.content for r in results)
        except Exception as e:
            self._error = str(e)
            chunks_text = ""
            results = []
            logger.exception("rag_retrieval_failed", component_id=self._id)

        self.set_output("content", chunks_text)
        self.set_output("chunks", [r.chunk.model_dump() for r in results])
        self.set_output("count", len(results))
        self._context.set_component_output(self._id, self._outputs)
        return self._outputs
