"""mDNS/zeroconf service discovery for local network services."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Dict, List

from zeroconf import ServiceBrowser, Zeroconf


@dataclass
class DiscoveredService:
    name: str
    service_type: str
    host: str
    port: int
    properties: Dict[str, str]


class _Listener:
    def __init__(self) -> None:
        self.services: Dict[str, DiscoveredService] = {}

    def remove_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        self.services.pop(name, None)

    def add_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        info = zc.get_service_info(service_type, name)
        if not info or not info.addresses:
            return
        host = socket.inet_ntoa(info.addresses[0])
        properties: Dict[str, str] = {}
        for key, value in (info.properties or {}).items():
            try:
                decoded_key = key.decode("utf-8") if isinstance(key, (bytes, bytearray)) else str(key)
                decoded_val = (
                    value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else str(value)
                )
                properties[decoded_key] = decoded_val
            except Exception:
                continue
        self.services[name] = DiscoveredService(
            name=name,
            service_type=service_type,
            host=host,
            port=info.port,
            properties=properties,
        )

    def update_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        self.add_service(zc, service_type, name)


def discover_services(service_types: List[str], timeout: float = 3.0) -> List[DiscoveredService]:
    """Discover services for a list of service types within timeout seconds."""
    zeroconf = Zeroconf()
    listener = _Listener()
    browsers = [ServiceBrowser(zeroconf, stype, listener) for stype in service_types]
    try:
        time.sleep(timeout)
    finally:
        for browser in browsers:
            browser.cancel()
        zeroconf.close()
    return list(listener.services.values())
