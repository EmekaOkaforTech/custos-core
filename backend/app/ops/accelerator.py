from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AcceleratorStatus:
    type: str
    status: str
    detail: str | None = None
    temperature_c: float | None = None
    utilization_pct: float | None = None
    memory_pct: float | None = None
    throttled: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "status": self.status,
            "detail": self.detail,
            "temperature_c": self.temperature_c,
            "utilization_pct": self.utilization_pct,
            "memory_pct": self.memory_pct,
            "throttled": self.throttled,
        }


def _hailo_device_present() -> bool:
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


def _load_metric(name: str) -> float | None:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except Exception:
        return None


def get_accelerator_status() -> AcceleratorStatus:
    preferred = os.getenv("CUSTOS_ACCELERATOR", "hailo").lower().strip()
    if preferred not in {"hailo", "coral", "none"}:
        preferred = "hailo"

    temperature = _load_metric("CUSTOS_ACCEL_TEMP_C")
    utilization = _load_metric("CUSTOS_ACCEL_UTIL")
    memory_pct = _load_metric("CUSTOS_ACCEL_MEM")
    throttled = temperature is not None and temperature >= 85.0

    if preferred == "none":
        return AcceleratorStatus(
            type="none",
            status="disabled",
            detail="Accelerator disabled",
            temperature_c=temperature,
            utilization_pct=utilization,
            memory_pct=memory_pct,
            throttled=throttled,
        )

    coral_present = Path("/dev/apex_0").exists()

    if preferred == "coral":
        status = "available" if coral_present else "unavailable"
        detail = "Coral USB detected" if coral_present else "Coral USB not detected"
        return AcceleratorStatus(
            type="coral",
            status=status,
            detail=detail,
            temperature_c=temperature,
            utilization_pct=utilization,
            memory_pct=memory_pct,
            throttled=throttled,
        )

    hailo_present = _hailo_device_present()
    hailo_runtime = _hailort_available()
    if hailo_present and hailo_runtime:
        detail = "Hailo device detected"
        status = "available"
    elif hailo_present and not hailo_runtime:
        detail = "Hailo device present but HailoRT missing"
        status = "unavailable"
    elif hailo_runtime and not hailo_present:
        detail = "HailoRT installed but device not detected"
        status = "unavailable"
    else:
        detail = "Hailo device and runtime not detected"
        status = "unavailable"

    if status != "available" and coral_present:
        return AcceleratorStatus(
            type="coral",
            status="available",
            detail="Coral USB detected (fallback)",
            temperature_c=temperature,
            utilization_pct=utilization,
            memory_pct=memory_pct,
            throttled=throttled,
        )

    return AcceleratorStatus(
        type="hailo8",
        status=status,
        detail=detail,
        temperature_c=temperature,
        utilization_pct=utilization,
        memory_pct=memory_pct,
        throttled=throttled,
    )
