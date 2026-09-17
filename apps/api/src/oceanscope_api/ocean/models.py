from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from oceanscope_api.db.base import Base
from oceanscope_api.provenance.models import JSON_DOCUMENT, utc_now


class MarineForecastPoint(Base):
    __tablename__ = "marine_forecast_point"
    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "request_key",
            "valid_at",
            name="uq_marine_forecast_version_request_time",
        ),
        CheckConstraint("requested_latitude BETWEEN -90 AND 90", name="requested_latitude_range"),
        CheckConstraint(
            "requested_longitude BETWEEN -180 AND 180", name="requested_longitude_range"
        ),
        CheckConstraint("grid_latitude BETWEEN -90 AND 90", name="grid_latitude_range"),
        CheckConstraint("grid_longitude BETWEEN -180 AND 180", name="grid_longitude_range"),
        CheckConstraint(
            "wave_height_m IS NULL OR wave_height_m >= 0", name="wave_height_nonnegative"
        ),
        CheckConstraint(
            "wave_period_s IS NULL OR wave_period_s >= 0", name="wave_period_nonnegative"
        ),
        CheckConstraint(
            "ocean_current_velocity_kmh IS NULL OR ocean_current_velocity_kmh >= 0",
            name="current_velocity_nonnegative",
        ),
        Index("ix_marine_forecast_location", "location", postgresql_using="gist"),
        Index("ix_marine_forecast_request_time", "request_key", "valid_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_version.id", ondelete="RESTRICT"), nullable=False
    )
    ingestion_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="RESTRICT"), nullable=False
    )
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    requested_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    grid_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    grid_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    wave_height_m: Mapped[float | None] = mapped_column(Float)
    wave_direction_deg: Mapped[float | None] = mapped_column(Float)
    wave_period_s: Mapped[float | None] = mapped_column(Float)
    sea_surface_temperature_c: Mapped[float | None] = mapped_column(Float)
    ocean_current_velocity_kmh: Mapped[float | None] = mapped_column(Float)
    ocean_current_direction_deg: Mapped[float | None] = mapped_column(Float)
    sea_level_height_msl_m: Mapped[float | None] = mapped_column(Float)
    units: Mapped[dict[str, str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    normalization_version: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
