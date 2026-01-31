from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, Text, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NetworkSettings(Base):
    __tablename__ = "network_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discovery_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scan_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    manual_services: Mapped[str] = mapped_column(Text, default="[]")
    last_scan_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    inference_url: Mapped[str | None] = mapped_column(String, nullable=True)
    inference_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    inference_last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    inference_status: Mapped[str | None] = mapped_column(String, nullable=True)
