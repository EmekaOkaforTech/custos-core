import os
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient

from app.settings import get_qdrant_path

COLLECTION_NAME = "custos_captures"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


@lru_cache
def get_client() -> QdrantClient:
    path = get_qdrant_path()
    _ensure_dir(path)
    return QdrantClient(path=path)


def add_documents(documents: list[str], metadata: list[dict[str, Any]], ids: list[str]) -> None:
    if not documents:
        return
    client = get_client()
    client.add(
        collection_name=COLLECTION_NAME,
        documents=documents,
        metadata=metadata,
        ids=ids,
    )


def query_documents(query_text: str, limit: int = 5) -> list[dict[str, Any]]:
    client = get_client()
    try:
        results = client.query(
            collection_name=COLLECTION_NAME,
            query_text=query_text,
            limit=limit,
        )
    except Exception:
        return []
    points = getattr(results, "points", results)
    items: list[dict[str, Any]] = []
    for point in points:
        payload = getattr(point, "payload", None) or {}
        items.append(payload)
    return items
