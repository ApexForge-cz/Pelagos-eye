"""Add latest USGS earthquake event observations.

Revision ID: 20260917_0004
Revises: 20260917_0003
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260917_0004"
down_revision: str | Sequence[str] | None = "20260917_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_document = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "earthquake_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=100), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("depth_km", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("magnitude", sa.Float(), nullable=True),
        sa.Column("place", sa.String(length=500), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("provider_status", sa.String(length=50), nullable=True),
        sa.Column("tsunami", sa.Boolean(), nullable=False),
        sa.Column("significance", sa.Integer(), nullable=True),
        sa.Column("detail_url", sa.String(length=1000), nullable=True),
        sa.Column("normalization_version", sa.String(length=100), nullable=False),
        sa.Column("quality_flags", json_document, nullable=False),
        sa.Column("raw_record", json_document, nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "depth_km BETWEEN -100 AND 1000",
            name=op.f("ck_earthquake_event_depth_range"),
        ),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name=op.f("ck_earthquake_event_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name=op.f("ck_earthquake_event_longitude_range"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_run.id"],
            name=op.f("fk_earthquake_event_ingestion_run_id_ingestion_run"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["source_version.id"],
            name=op.f("fk_earthquake_event_source_version_id_source_version"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_earthquake_event")),
        sa.UniqueConstraint("event_id", name=op.f("uq_earthquake_event_event_id")),
    )
    op.create_index(
        "ix_earthquake_event_location",
        "earthquake_event",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index("ix_earthquake_event_time", "earthquake_event", ["event_time"], unique=False)
    op.create_index(
        "ix_earthquake_event_updated",
        "earthquake_event",
        ["provider_updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_earthquake_event_updated", table_name="earthquake_event")
    op.drop_index("ix_earthquake_event_time", table_name="earthquake_event")
    op.drop_index(
        "ix_earthquake_event_location",
        table_name="earthquake_event",
        postgresql_using="gist",
    )
    op.drop_table("earthquake_event")
