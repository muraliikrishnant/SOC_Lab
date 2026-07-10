"""Qdrant vector store + Ollama embeddings.

One collection holds three kinds of points, distinguished by a `type`
payload field: "alert" (past triaged alerts), "sigma" (SigmaHQ detection
rules), and "technique" (MITRE ATT&CK techniques). Embedding once at
write time and searching at read time is what keeps retrieval fast — the
LLM never re-reasons over raw history, it gets a handful of pre-computed
nearest neighbors.
"""
import logging
import uuid
from typing import Optional

import requests
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from . import config

log = logging.getLogger(__name__)

_client: Optional[QdrantClient] = None
_EMBED_DIM_CACHE: Optional[int] = None


def ollama_post(path: str, payload: dict, timeout: int = 60):
    """POST to Ollama, routed to the local container or to Ollama Cloud
    depending on whether the requested model is tagged "*:cloud" — cloud
    models don't run through the local server, they're a direct call to
    ollama.com authenticated with OLLAMA_API_KEY."""
    model = payload.get("model", "")
    if model.endswith(":cloud"):
        url = f"{config.OLLAMA_CLOUD_URL}{path}"
        headers = {"Authorization": f"Bearer {config.OLLAMA_API_KEY}"}
    else:
        url = f"{config.OLLAMA_URL}{path}"
        headers = {}
    return requests.post(url, json=payload, headers=headers, timeout=timeout)


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=config.QDRANT_URL)
    return _client


def embed(text: str) -> list[float]:
    resp = ollama_post(
        "/api/embeddings",
        {"model": config.EMBED_MODEL, "prompt": text[:8000]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def ensure_collection() -> None:
    global _EMBED_DIM_CACHE
    if _EMBED_DIM_CACHE is None:
        _EMBED_DIM_CACHE = len(embed("dimension probe"))
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if config.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(size=_EMBED_DIM_CACHE, distance=qmodels.Distance.COSINE),
        )


def upsert(point_id: str, text: str, payload: dict) -> None:
    ensure_collection()
    vector = embed(text)
    point_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, point_id))
    get_client().upsert(
        collection_name=config.QDRANT_COLLECTION,
        points=[qmodels.PointStruct(id=point_uuid, vector=vector, payload={**payload, "natural_id": point_id})],
    )


def search(text: str, top_k: int = 5, type_filter: Optional[str] = None) -> list[dict]:
    return search_by_vector(embed(text), top_k=top_k, type_filter=type_filter)


def search_by_vector(vector: list[float], top_k: int = 5, type_filter: Optional[str] = None) -> list[dict]:
    """Same as search(), but takes an already-computed embedding. Use this
    when running multiple type-filtered searches against the same query
    text (see retrieval.py) so each one doesn't cost its own round trip to
    the embedding model."""
    ensure_collection()
    query_filter = None
    if type_filter:
        query_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(key="type", match=qmodels.MatchValue(value=type_filter))]
        )
    hits = get_client().search(
        collection_name=config.QDRANT_COLLECTION,
        query_vector=vector,
        limit=top_k,
        query_filter=query_filter,
    )
    return [{"score": h.score, **h.payload} for h in hits]
