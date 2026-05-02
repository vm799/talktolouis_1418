"""Voyage AI text-embedding helper for MongoDB vector search.

Uses voyage-3.5-lite (1024 dimensions). The vector index in db/indexes.py
must use the same numDimensions value.

Voyage AI is MongoDB's embedding model provider. The free tier covers
generous monthly token limits suitable for starter and prototype workloads.
See https://docs.voyageai.com/ for model details and pricing.
"""

import os

import voyageai

EMBEDDING_MODEL = "voyage-3.5-lite"
EMBEDDING_DIMENSIONS = 1024

_client: voyageai.AsyncClient | None = None


def _get_client() -> voyageai.AsyncClient:
    global _client
    if _client is None:
        if not os.getenv("VOYAGE_API_KEY"):
            raise RuntimeError("VOYAGE_API_KEY environment variable is not set.")
        _client = voyageai.AsyncClient()
    return _client


async def embed_text(text: str, *, input_type: str | None = None) -> list[float]:
    """Return a 1024-dimensional embedding for a single text.

    Pass input_type="query" for query embeddings and input_type="document"
    for stored documents to get the best retrieval quality.
    """
    client = _get_client()
    result = await client.embed(
        texts=[text], model=EMBEDDING_MODEL, input_type=input_type
    )
    return result.embeddings[0]


async def embed_texts(
    texts: list[str], *, input_type: str | None = None
) -> list[list[float]]:
    """Batch-embed a list of texts (one HTTP round-trip)."""
    client = _get_client()
    result = await client.embed(texts=texts, model=EMBEDDING_MODEL, input_type=input_type)
    return result.embeddings
