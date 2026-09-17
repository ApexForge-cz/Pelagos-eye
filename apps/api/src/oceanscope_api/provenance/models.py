from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oceanscope_api.db.base import Base

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(UTC)


class RedistributionStatus(StrEnum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    UNREVIEWED = "unreviewed"


class PublicationStatus(StrEnum):
    PRODUCTION = "production"
    PROVISIONAL = "provisional"
    SUPERSEDED = "superseded"


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class SourceState(StrEnum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    DELAYED = "DELAYED"
    OFFLINE = "OFFLINE"


class QualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


QUALITY_CODES = (
    "missing_required",
    "invalid_coordinate",
    "invalid_timestamp",
    "out_of_range",
    "unknown_enum",
    "duplicate",
    "late_arrival",
    "stale",
    "identity_conflict",
    "implausible_motion",
    "coverage_unknown",
    "provider_revision",
)


class DataSource(Base):
    __tablename__ = "data_source"
    __table_args__ = (
        CheckConstraint(
            "redistribution_status IN ('allowed', 'restricted', 'prohibited', 'unreviewed')",
            name="redistribution_status",
        ),
        CheckConstraint(
            "redistribution_status = 'unreviewed' OR terms_reviewed_at IS NOT NULL",
            name="reviewed_terms_have_date",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    terms_url: Mapped[str | None] = mapped_column(Text)
    attribution_text: Mapped[str] = mapped_column(Text, nullable=False)
    license_identifier: Mapped[str | None] = mapped_column(String(100))
    redistribution_status: Mapped[str] = mapped_column(
        String(20), default=RedistributionStatus.UNREVIEWED.value, nullable=False
    )
    terms_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    versions: Mapped[list[SourceVersion]] = relationship(
        back_populates="data_source", cascade="all, delete-orphan"
    )
    ingestion_runs: Mapped[list[IngestionRun]] = relationship(back_populates="data_source")


class SourceVersion(Base):
    __tablename__ = "source_version"
    __table_args__ = (
        UniqueConstraint(
            "data_source_id", "data_version", name="uq_source_version_source_data_version"
        ),
        UniqueConstraint("id", "data_source_id", name="uq_source_version_source_version_source"),
        CheckConstraint(
            "publication_status IN ('production', 'provisional', 'superseded')",
            name="publication_status",
        ),
        CheckConstraint(
            "(checksum_algorithm IS NULL AND checksum IS NULL) OR "
            "(checksum_algorithm IS NOT NULL AND checksum IS NOT NULL)",
            name="checksum_pair",
        ),
        CheckConstraint(
            "published_at IS NULL OR retrieved_at >= published_at",
            name="retrieval_after_publication",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=False
    )
    data_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    publication_status: Mapped[str] = mapped_column(
        String(20), default=PublicationStatus.PRODUCTION.value, nullable=False
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksum_algorithm: Mapped[str | None] = mapped_column(String(20))
    checksum: Mapped[str | None] = mapped_column(String(256))
    artifact_reference: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    data_source: Mapped[DataSource] = relationship(back_populates="versions")


class IngestionRun(Base):
    __tablename__ = "ingestion_run"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_version_id", "data_source_id"],
            ["source_version.id", "source_version.data_source_id"],
            name="fk_ingestion_run_version_source",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "data_source_id", "idempotency_key", name="uq_ingestion_run_source_idempotency"
        ),
        CheckConstraint("status IN ('running', 'succeeded', 'partial', 'failed')", name="status"),
        CheckConstraint(
            "source_state IN ('LIVE', 'CACHED', 'DELAYED', 'OFFLINE')",
            name="source_state",
        ),
        CheckConstraint(
            "(source_state = 'CACHED' AND cache_age_seconds IS NOT NULL "
            "AND cache_age_seconds >= 0) OR "
            "(source_state <> 'CACHED' AND cache_age_seconds IS NULL)",
            name="cache_age_matches_state",
        ),
        CheckConstraint(
            "records_received >= 0 AND records_accepted >= 0 AND records_rejected >= 0",
            name="nonnegative_counts",
        ),
        CheckConstraint(
            "records_accepted + records_rejected <= records_received",
            name="bounded_counts",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at", name="finish_after_start"
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="completion_matches_status",
        ),
        CheckConstraint(
            "(status = 'failed' AND failure_reason IS NOT NULL) OR "
            "(status <> 'failed' AND failure_reason IS NULL)",
            name="failure_reason_matches_status",
        ),
        Index("ix_ingestion_run_source_started", "data_source_id", "started_at"),
        Index("ix_ingestion_run_status_started", "status", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=False
    )
    source_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=IngestionStatus.RUNNING.value, nullable=False
    )
    source_state: Mapped[str] = mapped_column(String(20), nullable=False)
    cache_age_seconds: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict, nullable=False)
    code_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    data_source: Mapped[DataSource] = relationship(back_populates="ingestion_runs")
    source_version: Mapped[SourceVersion | None] = relationship(viewonly=True)
    quality_issues: Mapped[list[QualityIssue]] = relationship(
        back_populates="ingestion_run", cascade="all, delete-orphan"
    )


class QualityIssue(Base):
    __tablename__ = "quality_issue"
    __table_args__ = (
        UniqueConstraint("ingestion_run_id", "code", name="uq_quality_issue_run_quality_code"),
        CheckConstraint(
            "code IN (" + ", ".join(f"'{code}'" for code in QUALITY_CODES) + ")",
            name="code",
        ),
        CheckConstraint("severity IN ('info', 'warning', 'error')", name="severity"),
        CheckConstraint("record_count > 0", name="positive_record_count"),
        Index("ix_quality_issue_code", "code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ingestion_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ingestion_run.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sample_reference: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="quality_issues")
