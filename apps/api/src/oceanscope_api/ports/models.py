from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from oceanscope_api.db.base import Base
from oceanscope_api.provenance.models import JSON_DOCUMENT, utc_now


class PortSourceRecord(Base):
    __tablename__ = "port_source_record"
    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "source_record_key",
            name="uq_port_source_record_version_key",
        ),
        CheckConstraint("record_type IN ('unlocode', 'wpi')", name="record_type"),
        CheckConstraint("length(country_code) = 2", name="country_code_length"),
        CheckConstraint("un_locode IS NULL OR length(un_locode) = 5", name="un_locode_length"),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND location IS NULL) OR "
            "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 "
            "AND location IS NOT NULL)",
            name="coordinate_bundle",
        ),
        Index("ix_port_source_record_location", "location", postgresql_using="gist"),
        Index("ix_port_source_record_un_locode", "un_locode"),
        Index("ix_port_source_record_country_name", "country_code", "name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_version.id", ondelete="RESTRICT"), nullable=False
    )
    ingestion_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="RESTRICT"), nullable=False
    )
    source_record_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    un_locode: Mapped[str | None] = mapped_column(String(5))
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    location: Mapped[Any | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    coordinate_accuracy: Mapped[str | None] = mapped_column(String(50))
    function_code: Mapped[str | None] = mapped_column(String(20))
    source_status: Mapped[str | None] = mapped_column(String(20))
    source_updated_value: Mapped[str | None] = mapped_column(String(50))
    normalization_version: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
