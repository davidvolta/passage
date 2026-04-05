"""Search logic — embed a query and find matching passages in Qdrant."""

import os
from qdrant_client import QdrantClient
from openai import OpenAI

import config

_openai: OpenAI | None = None
_qdrant: QdrantClient | None = None


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        _openai = OpenAI(api_key=api_key)
    return _openai


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(path=str(config.DB_DIR))
    return _qdrant


def search(query: str, top_n: int = config.DEFAULT_TOP_N) -> list[dict]:
    """Embed query and return top_n matching passages."""
    top_n = min(top_n, config.MAX_TOP_N)

    # Embed the query
    resp = _get_openai().embeddings.create(
        model=config.OPENAI_EMBED_MODEL,
        input=query,
    )
    query_vector = resp.data[0].embedding

    # Search Qdrant
    results = _get_qdrant().query_points(
        collection_name=config.QDRANT_COLLECTION,
        query=query_vector,
        limit=top_n,
        with_payload=True,
    )

    passages = []
    for point in results.points:
        p = point.payload
        passages.append({
            "chunk_id": p["chunk_id"],
            "book_title": p["book_title"],
            "text": p["text"],
            "word_count": p["word_count"],
            "score": point.score,
        })

    return passages
