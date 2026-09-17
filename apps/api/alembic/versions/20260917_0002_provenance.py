"""Add the Phase 2 source catalog and provenance schema.

Revision ID: 20260917_0002
Revises: 20260917_0001
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260917_0002"
down_revision: str | Sequence[str] | None = "20260917_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_document = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "data_source",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("terms_url", sa.Text(), nullable=True),
        sa.Column("attribution_text", sa.Text(), nullable=False),
        sa.Column("license_identifier", sa.String(length=100), nullable=True),
        sa.Column("redistribution_status", sa.String(length=20), nullable=False),
        sa.Column("terms_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "redistribution_status IN ('allowed', 'restricted', 'prohibited', 'unreviewed')",
            name=op.f("ck_data_source_redistribution_status"),
        ),
        sa.CheckConstraint(
            "redistribution_status = 'unreviewed' OR terms_reviewed_at IS NOT NULL",
            name=op.f("ck_data_source_reviewed_terms_have_date"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_data_source"),
        sa.UniqueConstraint("slug", name="uq_data_source_slug"),
    )
    op.create_table(
        "source_version",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("data_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("publication_status", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checksum_algorithm", sa.String(length=20), nullable=True),
        sa.Column("checksum", sa.String(length=256), nullable=True),
        sa.Column("artifact_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "publication_status IN ('production', 'provisional', 'superseded')",
            name=op.f("ck_source_version_publication_status"),
        ),
        sa.CheckConstraint(
            "(checksum_algorithm IS NULL AND checksum IS NULL) OR "
            "(checksum_algorithm IS NOT NULL AND checksum IS NOT NULL)",
            name=op.f("ck_source_version_checksum_pair"),
        ),
        sa.CheckConstraint(
            "published_at IS NULL OR retrieved_at >= published_at",
            name=op.f("ck_source_version_retrieval_after_publication"),
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_source.id"],
            name="fk_source_version_data_source_id_data_source",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_version"),
        sa.UniqueConstraint(
            "data_source_id", "data_version", name="uq_source_version_source_data_version"
        ),
        sa.UniqueConstraint("id", "data_source_id", name="uq_source_version_source_version_source"),
    )
    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_state", sa.String(length=20), nullable=False),
        sa.Column("cache_age_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_accepted", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("parameters", json_document, nullable=False),
        sa.Column("code_revision", sa.String(length=100), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'partial', 'failed')",
            name=op.f("ck_ingestion_run_status"),
        ),
        sa.CheckConstraint(
            "source_state IN ('LIVE', 'CACHED', 'DELAYED', 'OFFLINE')",
            name=op.f("ck_ingestion_run_source_state"),
        ),
        sa.CheckConstraint(
            "(source_state = 'CACHED' AND cache_age_seconds IS NOT NULL "
            "AND cache_age_seconds >= 0) OR "
            "(source_state <> 'CACHED' AND cache_age_seconds IS NULL)",
            name=op.f("ck_ingestion_run_cache_age_matches_state"),
        ),
        sa.CheckConstraint(
            "records_received >= 0 AND records_accepted >= 0 AND records_rejected >= 0",
            name=op.f("ck_ingestion_run_nonnegative_counts"),
        ),
        sa.CheckConstraint(
            "records_accepted + records_rejected <= records_received",
            name=op.f("ck_ingestion_run_bounded_counts"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_ingestion_run_finish_after_start"),
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name=op.f("ck_ingestion_run_completion_matches_status"),
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND failure_reason IS NOT NULL) OR "
            "(status <> 'failed' AND failure_reason IS NULL)",
            name=op.f("ck_ingestion_run_failure_reason_matches_status"),
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_source.id"],
            name="fk_ingestion_run_data_source_id_data_source",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id", "data_source_id"],
            ["source_version.id", "source_version.data_source_id"],
            name="fk_ingestion_run_version_source",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_run"),
        sa.UniqueConstraint(
            "data_source_id", "idempotency_key", name="uq_ingestion_run_source_idempotency"
        ),
    )
    op.create_index(
        "ix_ingestion_run_source_started",
        "ingestion_run",
        ["data_source_id", "started_at"],
    )
    op.create_index("ix_ingestion_run_status_started", "ingestion_run", ["status", "started_at"])
    op.create_table(
        "quality_issue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sample_reference", sa.Text(), nullable=True),
        sa.Column("details", json_document, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "code IN ('missing_required', 'invalid_coordinate', 'invalid_timestamp', "
            "'out_of_range', 'unknown_enum', 'duplicate', 'late_arrival', 'stale', "
            "'identity_conflict', 'implausible_motion', 'coverage_unknown', "
            "'provider_revision')",
            name=op.f("ck_quality_issue_code"),
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name=op.f("ck_quality_issue_severity"),
        ),
        sa.CheckConstraint("record_count > 0", name=op.f("ck_quality_issue_positive_record_count")),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_run.id"],
            name="fk_quality_issue_ingestion_run_id_ingestion_run",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quality_issue"),
        sa.UniqueConstraint("ingestion_run_id", "code", name="uq_quality_issue_run_quality_code"),
    )
    op.create_index("ix_quality_issue_code", "quality_issue", ["code"])


def downgrade() -> None:
    op.drop_index("ix_quality_issue_code", table_name="quality_issue")
    op.drop_table("quality_issue")
    op.drop_index("ix_ingestion_run_status_started", table_name="ingestion_run")
    op.drop_index("ix_ingestion_run_source_started", table_name="ingestion_run")
    op.drop_table("ingestion_run")
    op.drop_table("source_version")
    op.drop_table("data_source")
