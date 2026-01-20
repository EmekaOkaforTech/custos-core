from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.security import clear_admin_key, get_admin_key, set_admin_key
from app.settings import admin_api_enabled, get_admin_bootstrap_key, get_env

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RotateRequest(BaseModel):
    new_key: str = Field(min_length=1)


def _require_admin_key(x_api_key: str | None) -> None:
    current = get_admin_key()
    if not current or x_api_key != current:
        raise HTTPException(status_code=401, detail="Invalid admin key.")


@router.get("/settings")
def get_settings(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
    if not admin_api_enabled():
        raise HTTPException(status_code=404, detail="Admin API disabled.")
    configured = bool(get_admin_key())
    if configured:
        _require_admin_key(x_api_key)
    return {
        "admin_api_enabled": True,
        "key_configured": configured,
        "rotation_supported": True,
        "bootstrap_supported": get_env() == "dev" and bool(get_admin_bootstrap_key()),
    }


@router.post("/api-key/rotate")
def rotate_key(
    payload: RotateRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    if not admin_api_enabled():
        raise HTTPException(status_code=404, detail="Admin API disabled.")

    current = get_admin_key()
    if not current:
        bootstrap = get_admin_bootstrap_key()
        provided = (x_api_key or "").strip()
        if get_env() != "dev" or not bootstrap or provided != bootstrap:
            raise HTTPException(status_code=401, detail="Admin key not configured.")
    else:
        _require_admin_key(x_api_key)

    set_admin_key(payload.new_key)
    return {"status": "rotated"}


@router.post("/api-key/clear")
def clear_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
    if not admin_api_enabled():
        raise HTTPException(status_code=404, detail="Admin API disabled.")
    if get_env() != "dev":
        raise HTTPException(status_code=403, detail="Clear is dev-only.")
    _require_admin_key(x_api_key)
    clear_admin_key()
    return {"status": "cleared"}
