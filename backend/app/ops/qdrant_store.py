import os
import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient

from app.settings import get_qdrant_path, get_qdrant_url

COLLECTION_NAME = "custos_captures"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


@lru_cache
def get_client() -> QdrantClient:
    url = get_qdrant_url()
    if url:
        return QdrantClient(url=url)
    path = get_qdrant_path()
    _ensure_dir(path)
    return QdrantClient(path=path)


def _to_point_id(raw_id: str) -> str:
    # Qdrant only accepts UUID or unsigned int IDs.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, raw_id))


def add_documents(documents: list[str], metadata: list[dict[str, Any]], ids: list[str]) -> None:
    if not documents:
        return
    point_ids = [_to_point_id(item) for item in ids]
    client = get_client()
    client.add(
        collection_name=COLLECTION_NAME,
        documents=documents,
        metadata=metadata,
        ids=point_ids,
    )


def query_documents(query_text: str, limit: int = 5) -> list[dict[str, Any]]:
    client = get_client()
    try:
        results = client.query(
            collection_name=COLLECTION_NAME,
            query_text=query_text,
            limit=limit,
        )
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
    points = getattr(results, "points", results) or []
    ids = [getattr(point, "id", None) for point in points if getattr(point, "id", None) is not None]
    items: list[dict[str, Any]] = []
    if ids:
        try:
            payload_points = client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=ids,
                with_payload=True,
            )
            payload_by_id = {point.id: (point.payload or {}) for point in payload_points}
            for point_id in ids:
                items.append(payload_by_id.get(point_id, {}))
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
    return items
