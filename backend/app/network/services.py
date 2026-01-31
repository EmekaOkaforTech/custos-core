"""Service normalization and settings merge for network discovery."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from app.models.network_settings import NetworkSettings
from app.db import SessionLocal
from .discovery import DiscoveredService, discover_services

SERVICE_TYPES = [
    "_smb._tcp.local.",
    "_nfs._tcp.local.",
    "_http._tcp.local.",
    "_custos-inference._tcp.local.",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_service(item: DiscoveredService) -> Dict[str, str]:
    svc_type = "other"
    protocol = "http"
    if item.service_type.startswith("_smb"):
        svc_type = "nas"
        protocol = "smb"
    elif item.service_type.startswith("_nfs"):
        svc_type = "nas"
        protocol = "nfs"
    elif "inference" in item.service_type:
        svc_type = "inference"
        protocol = "http"
    return {
        "id": f"discovered:{item.name}",
        "name": item.name,
        "type": svc_type,
        "protocol": protocol,
        "host": item.host,
        "port": item.port,
        "status": "available",
        "source": "discovered",
        "properties": item.properties,
    }


def get_or_create_settings(db=None) -> NetworkSettings:
    owns = False
    if db is None:
        db = SessionLocal()
        owns = True
    settings = db.query(NetworkSettings).first()
    if not settings:
        settings = NetworkSettings(
            discovery_enabled=True,
            scan_interval_minutes=15,
            manual_services="[]",
            last_scan_at=None,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    if owns:
        db.close()
    return settings


def get_discovered_services(settings: NetworkSettings) -> List[Dict[str, str]]:
    if not settings.discovery_enabled:
        return []
    services = discover_services(SERVICE_TYPES, timeout=3.0)
    return [_normalize_service(item) for item in services]


def merge_services(discovered: List[Dict[str, str]], manual: List[Dict[str, str]]) -> List[Dict[str, str]]:
    combined = list(discovered)
    for item in manual:
        normalized = {
            "id": f"manual:{item.get('host')}:{item.get('port')}",
            "name": item.get("name") or item.get("host"),
            "type": item.get("type") or "other",
            "protocol": item.get("protocol") or "http",
            "host": item.get("host"),
            "port": item.get("port"),
            "status": "manual",
            "source": "manual",
            "properties": {},
        }
        combined.append(normalized)
    return combined


def scan_services(db=None) -> Dict[str, object]:
    owns = False
    if db is None:
        db = SessionLocal()
        owns = True
    settings = get_or_create_settings(db)
    discovered = get_discovered_services(settings)
    manual_services = []
    if settings.manual_services:
        try:
            manual_services = json.loads(settings.manual_services)
        except json.JSONDecodeError:
            manual_services = []
    merged = merge_services(discovered, manual_services)
    settings.last_scan_at = _now_iso()
    db.add(settings)
    db.commit()
    if owns:
        db.close()
    return {
        "services": merged,
        "last_scan": settings.last_scan_at,
    }
