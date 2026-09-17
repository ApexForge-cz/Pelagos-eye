from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from oceanscope_api.db.base import Base
from oceanscope_api.provenance.models import JSON_DOCUMENT, utc_now


class EarthquakeEvent(Base):
    __tablename__ = "earthquake_event"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint("depth_km BETWEEN -100 AND 1000", name="depth_range"),
        Index("ix_earthquake_event_location", "location", postgresql_using="gist"),
        Index("ix_earthquake_event_time", "event_time"),
        Index("ix_earthquake_event_updated", "provider_updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_version.id", ondelete="RESTRICT"), nullable=False
    )
    ingestion_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="RESTRICT"), nullable=False
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    magnitude: Mapped[float | None] = mapped_column(Float)
    place: Mapped[str | None] = mapped_column(String(500))
    event_type: Mapped[str | None] = mapped_column(String(100))
    provider_status: Mapped[str | None] = mapped_column(String(50))
    tsunami: Mapped[bool] = mapped_column(Boolean, nullable=False)
    significance: Mapped[int | None] = mapped_column(Integer)
    detail_url: Mapped[str | None] = mapped_column(String(1000))
    normalization_version: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
