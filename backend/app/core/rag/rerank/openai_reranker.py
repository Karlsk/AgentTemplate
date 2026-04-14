from __future__ import annotations

from app.core.common.logging import TerraLogUtil as logger
import time

import httpx
import numpy as np
from typing import Any

from app.core.common.config import settings as app_settings
from app.core.rag.models.search import ScoredDocument
from app.core.rag.rerank.base import BaseReranker

class OpenAIReranker(BaseReranker):
    """Reranker using OpenAI-compatible /rerank endpoint.

    Works with Jina, Cohere, and other providers that expose an OpenAI-compatible rerank API.
    """

    def __init__(self, settings: Any | None = None, model: str | None = None):
        s = settings or app_settings
        self._model = model or getattr(s, "RERANK_MODEL", "rerank-english-v3.0")
        self._base_url = getattr(s, "OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self._api_key = getattr(s, "OPENAI_API_KEY", "")
        self._timeout = getattr(s, "LLM_TIMEOUT", 600)

    def rerank(self, query: str, documents: list[ScoredDocument], top_k: int | None = None) -> list[ScoredDocument]:
        if not documents:
            return []

        texts = [doc.chunk.content for doc in documents]
        t0 = time.monotonic()
        scores = self._call_api(query, texts, top_k)

        result = []
        for i, doc in enumerate(documents):
            result.append(
                ScoredDocument(
                    chunk=doc.chunk,
                    score=scores[i],
                    vector_score=doc.vector_score,
                    keyword_score=doc.keyword_score,
                )
            )

        result.sort(key=lambda x: x.score, reverse=True)
        if top_k:
            result = result[:top_k]
        logger.info(
            "rag_rerank_completed",
            in_count=len(documents),
            out_count=len(result),
            elapsed_s=time.monotonic() - t0,
        )
        return result

    def _call_api(self, query: str, texts: list[str], top_k: int | None) -> np.ndarray:
        payload = {
            "model": self._model,
            "query": query,
            "documents": texts,
        }
        if top_k:
            payload["top_n"] = top_k

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        url = f"{self._base_url}/rerank"

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        scores = np.zeros(len(texts))
        for item in data.get("results", []):
            idx = item["index"]
            scores[idx] = item.get("relevance_score", 0.0)

        return self._normalize_scores(scores)
