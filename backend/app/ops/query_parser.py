import json
import os
import re
from typing import Any, Dict, Tuple

import httpx


def _is_local_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return (
        lowered.startswith("http://127.")
        or lowered.startswith("http://localhost")
        or lowered.startswith("http://192.")
        or lowered.startswith("http://10.")
        or lowered.startswith("http://172.16.")
        or lowered.startswith("http://172.17.")
        or lowered.startswith("http://172.18.")
        or lowered.startswith("http://172.19.")
        or lowered.startswith("http://172.2")
        or lowered.startswith("http://172.30.")
        or lowered.startswith("http://172.31.")
    )


_CAPTURE_TYPES = {
    "decision": "decision",
    "decisions": "decision",
    "note": "notes",
    "notes": "notes",
    "reflection": "reflection",
    "reflections": "reflection",
    "follow-up": "follow-up",
    "followups": "follow-up",
    "follow-up": "follow-up",
    "transcript": "transcript",
    "transcripts": "transcript",
    "email": "email",
    "chat": "chat",
}

_DATE_RANGE_PATTERNS = [
    re.compile(r"between\s+(?P<start>[^\s]+)\s+and\s+(?P<end>[^\s]+)", re.I),
    re.compile(r"from\s+(?P<start>[^\s]+)\s+to\s+(?P<end>[^\s]+)", re.I),
    re.compile(r"since\s+(?P<start>[^\s]+)", re.I),
    re.compile(r"after\s+(?P<start>[^\s]+)", re.I),
    re.compile(r"before\s+(?P<end>[^\s]+)", re.I),
]


def _extract_filters(text: str) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    lowered = text.lower()

    capture_types = []
    for token, normalized in _CAPTURE_TYPES.items():
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            capture_types.append(normalized)
    if capture_types:
        filters["capture_types"] = sorted(set(capture_types))

    for pattern in _DATE_RANGE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if match.groupdict().get("start"):
            filters["start"] = match.group("start")
        if match.groupdict().get("end"):
            filters["end"] = match.group("end")
        break

    person_match = re.search(r"(?:with|from|for)\s+(?P<person>[A-Z][\w\s\-']{1,60})", text)
    if person_match:
        filters["person"] = person_match.group("person").strip()

    context_match = re.search(r"context\s+(?P<context>[^\n]+)", text, re.I)
    if context_match:
        filters["context"] = context_match.group("context").strip()

    return filters


def _infer_intent(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["summarize", "summary"]):
        return "summarize"
    if any(word in lowered for word in ["filter", "only"]):
        return "filter"
    if any(word in lowered for word in ["find", "search", "show", "list", "what", "when"]):
        return "search"
    return "unknown"


def parse_query(text: str) -> Tuple[Dict[str, Any], bool]:
    text = (text or "").strip()
    if not text:
        return {"intent": "search", "filters": {}, "tokens": []}, False

    filters = _extract_filters(text)
    intent = _infer_intent(text)

    if intent != "unknown":
        return {"intent": intent, "filters": filters, "tokens": text.split()}, False

    llm_url = os.getenv("CUSTOS_QUERY_LLM_URL", "")
    if not _is_local_url(llm_url):
        return {"intent": "search", "filters": filters, "tokens": text.split(), "note": "llm_unavailable"}, False

    payload = {"query": text, "mode": "parse"}
    try:
        response = httpx.post(llm_url, json=payload, timeout=30)
        if response.status_code != 200:
            return {"intent": "search", "filters": filters, "tokens": text.split(), "note": "llm_error"}, False
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return {"intent": "search", "filters": filters, "tokens": text.split(), "note": "llm_error"}, False

    intent = data.get("intent") or "search"
    parsed_filters = data.get("filters") or {}
    if filters:
        parsed_filters = {**parsed_filters, **filters}

    return {"intent": intent, "filters": parsed_filters, "tokens": text.split()}, True
