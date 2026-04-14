"""Retrieval strategies using LlamaIndex.

Provides vector, keyword (BM25), and hybrid (RRF-fused) retrievers
that operate over the shared PGVectorStore.
"""

import re
import time
from typing import Any, Dict, List, Optional

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from rank_bm25 import BM25Okapi

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil
from app.core.rag.storage.vector_store import (
    build_kb_filters,
    get_vector_store,
    query_vectors,
)


# ------------------------------------------------------------------ #
#  Vector Retriever                                                    #
# ------------------------------------------------------------------ #

async def vector_search(
    query: str,
    embed_model: BaseEmbedding,
    kb_ids: List[int],
    workspace_id: int,
    top_k: int = 5,
    score_threshold: float = 0.0,
) -> List[NodeWithScore]:
    """Pure vector similarity search.

    Args:
        query: Natural-language query.
        embed_model: Embedding model to encode the query.
        kb_ids: Knowledge base IDs to search in.
        workspace_id: Workspace scope.
        top_k: Number of results.
        score_threshold: Minimum cosine similarity.

    Returns:
        List of NodeWithScore objects, sorted by score desc.
    """
    t0 = time.perf_counter()
    query_embedding = await embed_model.aget_query_embedding(query)
    embed_ms = round((time.perf_counter() - t0) * 1000, 2)

    filters = build_kb_filters(kb_ids, workspace_id)

    t0 = time.perf_counter()
    result: VectorStoreQueryResult = query_vectors(
        query_embedding=query_embedding,
        top_k=top_k,
        filters=filters,
    )
    search_ms = round((time.perf_counter() - t0) * 1000, 2)

    nodes_with_scores: List[NodeWithScore] = []
    if result.nodes and result.similarities:
        for node, sim in zip(result.nodes, result.similarities, strict=True):
            if sim is not None and sim >= score_threshold:
                nodes_with_scores.append(
                    NodeWithScore(node=node, score=float(sim)))

    TerraLogUtil.info(
        "vector_search_completed",
        result_count=len(nodes_with_scores),
        embed_ms=embed_ms,
        search_ms=search_ms,
    )
    return nodes_with_scores


# ------------------------------------------------------------------ #
#  Keyword (BM25) Retriever                                            #
# ------------------------------------------------------------------ #

async def keyword_search(
    query: str,
    embed_model: BaseEmbedding,
    kb_ids: List[int],
    workspace_id: int,
    top_k: int = 20,
) -> List[NodeWithScore]:
    """BM25 keyword search over the vector store corpus.

    Fetches a broad set of candidates via vector search (relaxed top-k),
    then re-scores them with BM25 for keyword relevance.

    Args:
        query: Natural-language query.
        embed_model: Embedding model (used to fetch candidate pool).
        kb_ids: Knowledge base IDs.
        workspace_id: Workspace scope.
        top_k: Number of results to return.

    Returns:
        List of NodeWithScore objects re-scored by BM25.
    """
    # Fetch a broad candidate pool via vector search
    candidate_pool_size = max(top_k * 5, 100)
    candidates = await vector_search(
        query=query,
        embed_model=embed_model,
        kb_ids=kb_ids,
        workspace_id=workspace_id,
        top_k=candidate_pool_size,
        score_threshold=0.0,
    )

    if not candidates:
        return []

    # Build BM25 index over candidates
    corpus = [n.node.get_content() for n in candidates]
    tokenized_corpus = [_tokenize(doc) for doc in corpus]
    tokenized_query = _tokenize(query)

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    # Pair candidates with BM25 scores and sort
    scored = [
        NodeWithScore(node=candidates[i].node, score=float(scores[i]))
        for i in range(len(candidates))
        if scores[i] > 0
    ]
    scored.sort(key=lambda x: x.score, reverse=True)

    TerraLogUtil.info(
        "keyword_search_completed",
        candidate_count=len(candidates),
        result_count=min(top_k, len(scored)),
    )
    return scored[:top_k]


# ------------------------------------------------------------------ #
#  Hybrid Retriever (RRF)                                              #
# ------------------------------------------------------------------ #

async def hybrid_search(
    query: str,
    embed_model: BaseEmbedding,
    kb_ids: List[int],
    workspace_id: int,
    top_k: int = 5,
    score_threshold: float = 0.0,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    rrf_k: int = 60,
) -> List[NodeWithScore]:
    """Hybrid search combining vector and BM25 via Reciprocal Rank Fusion.

    Args:
        query: Natural-language query.
        embed_model: Embedding model.
        kb_ids: Knowledge base IDs.
        workspace_id: Workspace scope.
        top_k: Final number of results.
        score_threshold: Min score for vector results.
        vector_weight: RRF weight for vector results.
        keyword_weight: RRF weight for keyword results.
        rrf_k: RRF constant (default 60).

    Returns:
        Fused list of NodeWithScore sorted by RRF score.
    """
    # Run both retrievers
    vec_top = min(top_k * 3, 50)
    kw_top = settings.RAG_KEYWORD_TOP_K

    vector_results = await vector_search(
        query=query,
        embed_model=embed_model,
        kb_ids=kb_ids,
        workspace_id=workspace_id,
        top_k=vec_top,
        score_threshold=score_threshold,
    )

    keyword_results = await keyword_search(
        query=query,
        embed_model=embed_model,
        kb_ids=kb_ids,
        workspace_id=workspace_id,
        top_k=kw_top,
    )

    # RRF merge
    merged = _rrf_merge(
        vector_results,
        keyword_results,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        rrf_k=rrf_k,
    )

    TerraLogUtil.info(
        "hybrid_search_completed",
        vector_count=len(vector_results),
        keyword_count=len(keyword_results),
        merged_count=len(merged),
    )
    return merged[:top_k]


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _rrf_merge(
    vector_results: List[NodeWithScore],
    keyword_results: List[NodeWithScore],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    rrf_k: int = 60,
) -> List[NodeWithScore]:
    """Reciprocal Rank Fusion of two result lists.

    score = sum( weight / (k + rank) ) for each list.
    """
    scores: Dict[str, Dict[str, Any]] = {}

    for rank, nws in enumerate(vector_results):
        nid = nws.node.node_id
        rrf_score = vector_weight / (rrf_k + rank + 1)
        scores[nid] = {"node": nws.node, "score": rrf_score}

    for rank, nws in enumerate(keyword_results):
        nid = nws.node.node_id
        rrf_score = keyword_weight / (rrf_k + rank + 1)
        if nid in scores:
            scores[nid]["score"] += rrf_score
        else:
            scores[nid] = {"node": nws.node, "score": rrf_score}

    sorted_items = sorted(
        scores.values(), key=lambda x: x["score"], reverse=True)
    return [NodeWithScore(node=item["node"], score=item["score"]) for item in sorted_items]


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + CJK-character tokenizer."""
    tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower())
    return tokens
