from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .settings import get_data_dir


def _admin_key_path() -> Path:
    return Path(get_data_dir()) / "admin_api_key.json"


def get_admin_key() -> str:
    path = _admin_key_path()
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("key", ""))


def set_admin_key(value: str) -> None:
    path = _admin_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"key": value, "updated_at": datetime.utcnow().isoformat()}
    path.write_text(json.dumps(payload), encoding="utf-8")


def clear_admin_key() -> None:
    path = _admin_key_path()
    if path.exists():
        path.unlink()
