"""Reranker implementations using LlamaIndex node postprocessors.

Supports:
- cross-encoder reranking (sentence-transformers)
- no-op passthrough (default when reranking is disabled)
"""

from typing import List, Optional

from llama_index.core.schema import NodeWithScore, QueryBundle

from app.core.common.logging import TerraLogUtil


async def rerank_nodes(
    query: str,
    nodes: List[NodeWithScore],
    top_k: int = 5,
    model_name: str = "",
) -> List[NodeWithScore]:
    """Re-rank nodes for improved relevance.

    If *model_name* is empty or loading fails, falls back to a no-op
    (returns input truncated to *top_k*).

    Args:
        query: Original user query.
        nodes: Candidate nodes from retrieval.
        top_k: Number of results to keep.
        model_name: Cross-encoder model name
                     (e.g. ``cross-encoder/ms-marco-MiniLM-L-6-v2``).

    Returns:
        Re-ranked (or truncated) list of NodeWithScore.
    """
    if not nodes:
        return []

    if not model_name:
        return nodes[:top_k]

    try:
        return _cross_encoder_rerank(query, nodes, top_k, model_name)
    except Exception as exc:
        TerraLogUtil.exception("rerank_failed", error=str(exc))
        return nodes[:top_k]


def _cross_encoder_rerank(
    query: str,
    nodes: List[NodeWithScore],
    top_k: int,
    model_name: str,
) -> List[NodeWithScore]:
    """Score query-document pairs with a cross-encoder model.

    Uses ``sentence_transformers.CrossEncoder`` under the hood.

    Args:
        query: Query string.
        nodes: Candidate nodes.
        top_k: How many to return.
        model_name: HuggingFace cross-encoder model name.

    Returns:
        Re-ranked nodes.
    """
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(model_name)

    pairs = [(query, n.node.get_content()) for n in nodes]
    scores = model.predict(pairs)

    reranked = [
        NodeWithScore(node=n.node, score=float(s))
        for n, s in zip(nodes, scores, strict=True)
    ]
    reranked.sort(key=lambda x: x.score, reverse=True)

    TerraLogUtil.info(
        "cross_encoder_rerank_completed",
        input_count=len(nodes),
        output_count=min(top_k, len(reranked)),
        model_name=model_name,
    )
    return reranked[:top_k]
