from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AcceleratorStatus:
    type: str
    status: str
    detail: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "status": self.status,
            "detail": self.detail,
        }


def _hailo_device_present() -> bool:
    # Common device nodes; keep it simple and local-only.
    for path in ("/dev/hailo0", "/dev/hailo", "/dev/hailo-accel"):
        if Path(path).exists():
            return True
    return False


def _hailort_available() -> bool:
    try:
        import importlib

        importlib.import_module("hailort")
        return True
    except Exception:
        return False


def get_accelerator_status() -> AcceleratorStatus:
    preferred = os.getenv("CUSTOS_ACCELERATOR", "hailo").lower().strip()
    if preferred not in {"hailo", "coral", "none"}:
        preferred = "hailo"

    if preferred == "none":
        return AcceleratorStatus(type="none", status="disabled", detail="Accelerator disabled")

    if preferred == "coral":
        coral_present = Path("/dev/apex_0").exists()
        if coral_present:
            return AcceleratorStatus(type="coral", status="available", detail="Coral USB detected")
        return AcceleratorStatus(type="coral", status="unavailable", detail="Coral USB not detected")

    hailo_present = _hailo_device_present()
    hailo_runtime = _hailort_available()
    if hailo_present and hailo_runtime:
        return AcceleratorStatus(type="hailo8", status="available", detail="Hailo device detected")
    if hailo_present and not hailo_runtime:
        return AcceleratorStatus(type="hailo8", status="unavailable", detail="Hailo device present but HailoRT missing")
    if hailo_runtime and not hailo_present:
        return AcceleratorStatus(type="hailo8", status="unavailable", detail="HailoRT installed but device not detected")
    return AcceleratorStatus(type="hailo8", status="unavailable", detail="Hailo device and runtime not detected")
