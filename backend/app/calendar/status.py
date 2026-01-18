import json
from datetime import datetime
from pathlib import Path

from app.settings import get_data_dir

STATUS_FILE = "calendar_status.json"


def _status_path() -> Path:
    return Path(get_data_dir()) / STATUS_FILE


def read_status() -> dict:
    path = _status_path()
    if not path.exists():
        return {
            "enabled": False,
            "last_success": None,
            "last_error": None,
            "last_attempt": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(payload: dict) -> None:
    data_dir = Path(get_data_dir())
    data_dir.mkdir(parents=True, exist_ok=True)
    with _status_path().open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def mark_attempt(enabled: bool, error: str | None = None) -> None:
    payload = read_status()
    payload["enabled"] = enabled
    payload["last_attempt"] = datetime.utcnow().isoformat()
    if error:
        payload["last_error"] = error
    write_status(payload)


def mark_success(enabled: bool) -> None:
    payload = read_status()
    payload["enabled"] = enabled
    payload["last_attempt"] = datetime.utcnow().isoformat()
    payload["last_success"] = datetime.utcnow().isoformat()
    payload["last_error"] = None
    write_status(payload)
