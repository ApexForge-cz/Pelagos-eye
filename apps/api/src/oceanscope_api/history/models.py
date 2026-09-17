from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from oceanscope_api.db.base import Base
from oceanscope_api.provenance.models import JSON_DOCUMENT, utc_now


class HistoricalAisPosition(Base):
    __tablename__ = "historical_ais_position"
    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "record_fingerprint",
            name="uq_historical_ais_version_fingerprint",
        ),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint("sog_knots IS NULL OR sog_knots >= 0", name="sog_nonnegative"),
        CheckConstraint("cog_deg IS NULL OR (cog_deg >= 0 AND cog_deg < 360)", name="cog_range"),
        CheckConstraint(
            "heading_deg IS NULL OR (heading_deg >= 0 AND heading_deg < 360)",
            name="heading_range",
        ),
        Index("ix_historical_ais_location", "location", postgresql_using="gist"),
        Index("ix_historical_ais_observed_at", "observed_at"),
        Index("ix_historical_ais_mmsi_time", "mmsi", "observed_at"),
        Index("ix_historical_ais_request", "request_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_version.id", ondelete="RESTRICT"), nullable=False
    )
    ingestion_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="RESTRICT"), nullable=False
    )
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    record_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    archive_date: Mapped[date] = mapped_column(Date, nullable=False)
    mmsi: Mapped[str] = mapped_column(String(9), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    sog_knots: Mapped[float | None] = mapped_column(Float)
    cog_deg: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    vessel_name: Mapped[str | None] = mapped_column(String(200))
    imo: Mapped[str | None] = mapped_column(String(30))
    call_sign: Mapped[str | None] = mapped_column(String(50))
    vessel_type: Mapped[int | None] = mapped_column(Integer)
    navigation_status: Mapped[int | None] = mapped_column(Integer)
    length_m: Mapped[float | None] = mapped_column(Float)
    width_m: Mapped[float | None] = mapped_column(Float)
    draft_m: Mapped[float | None] = mapped_column(Float)
    cargo: Mapped[str | None] = mapped_column(String(100))
    transceiver_class: Mapped[str | None] = mapped_column(String(20))
    normalization_version: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
