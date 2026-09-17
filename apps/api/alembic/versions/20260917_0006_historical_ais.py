"""Add bounded NOAA MarineCadastre historical AIS positions.

Revision ID: 20260917_0006
Revises: 20260917_0005
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260917_0006"
down_revision: str | Sequence[str] | None = "20260917_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_document = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "historical_ais_position",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=False),
        sa.Column("record_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("archive_date", sa.Date(), nullable=False),
        sa.Column("mmsi", sa.String(length=9), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("sog_knots", sa.Float(), nullable=True),
        sa.Column("cog_deg", sa.Float(), nullable=True),
        sa.Column("heading_deg", sa.Float(), nullable=True),
        sa.Column("vessel_name", sa.String(length=200), nullable=True),
        sa.Column("imo", sa.String(length=30), nullable=True),
        sa.Column("call_sign", sa.String(length=50), nullable=True),
        sa.Column("vessel_type", sa.Integer(), nullable=True),
        sa.Column("navigation_status", sa.Integer(), nullable=True),
        sa.Column("length_m", sa.Float(), nullable=True),
        sa.Column("width_m", sa.Float(), nullable=True),
        sa.Column("draft_m", sa.Float(), nullable=True),
        sa.Column("cargo", sa.String(length=100), nullable=True),
        sa.Column("transceiver_class", sa.String(length=20), nullable=True),
        sa.Column("normalization_version", sa.String(length=100), nullable=False),
        sa.Column("quality_flags", json_document, nullable=False),
        sa.Column("raw_record", json_document, nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "cog_deg IS NULL OR (cog_deg >= 0 AND cog_deg < 360)",
            name=op.f("ck_historical_ais_position_cog_range"),
        ),
        sa.CheckConstraint(
            "heading_deg IS NULL OR (heading_deg >= 0 AND heading_deg < 360)",
            name=op.f("ck_historical_ais_position_heading_range"),
        ),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name=op.f("ck_historical_ais_position_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name=op.f("ck_historical_ais_position_longitude_range"),
        ),
        sa.CheckConstraint(
            "sog_knots IS NULL OR sog_knots >= 0",
            name=op.f("ck_historical_ais_position_sog_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_run.id"],
            name=op.f("fk_historical_ais_position_ingestion_run_id_ingestion_run"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["source_version.id"],
            name=op.f("fk_historical_ais_position_source_version_id_source_version"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_ais_position")),
        sa.UniqueConstraint(
            "source_version_id",
            "record_fingerprint",
            name="uq_historical_ais_version_fingerprint",
        ),
    )
    op.create_index(
        "ix_historical_ais_location",
        "historical_ais_position",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_historical_ais_mmsi_time",
        "historical_ais_position",
        ["mmsi", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_historical_ais_observed_at",
        "historical_ais_position",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_historical_ais_request",
        "historical_ais_position",
        ["request_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_historical_ais_request", table_name="historical_ais_position")
    op.drop_index("ix_historical_ais_observed_at", table_name="historical_ais_position")
    op.drop_index("ix_historical_ais_mmsi_time", table_name="historical_ais_position")
    op.drop_index(
        "ix_historical_ais_location",
        table_name="historical_ais_position",
        postgresql_using="gist",
    )
    op.drop_table("historical_ais_position")
