"""Add PostGIS-backed official port source records.

Revision ID: 20260917_0003
Revises: 20260917_0002
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260917_0003"
down_revision: str | Sequence[str] | None = "20260917_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_document = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "port_source_record",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_key", sa.String(length=160), nullable=False),
        sa.Column("source_record_id", sa.String(length=100), nullable=False),
        sa.Column("record_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("un_locode", sa.String(length=5), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("coordinate_accuracy", sa.String(length=50), nullable=True),
        sa.Column("function_code", sa.String(length=20), nullable=True),
        sa.Column("source_status", sa.String(length=20), nullable=True),
        sa.Column("source_updated_value", sa.String(length=50), nullable=True),
        sa.Column("normalization_version", sa.String(length=100), nullable=False),
        sa.Column("quality_flags", json_document, nullable=False),
        sa.Column("raw_record", json_document, nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "record_type IN ('unlocode', 'wpi')",
            name=op.f("ck_port_source_record_record_type"),
        ),
        sa.CheckConstraint(
            "length(country_code) = 2",
            name=op.f("ck_port_source_record_country_code_length"),
        ),
        sa.CheckConstraint(
            "un_locode IS NULL OR length(un_locode) = 5",
            name=op.f("ck_port_source_record_un_locode_length"),
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND location IS NULL) OR "
            "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 "
            "AND location IS NOT NULL)",
            name=op.f("ck_port_source_record_coordinate_bundle"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_run.id"],
            name=op.f("fk_port_source_record_ingestion_run_id_ingestion_run"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["source_version.id"],
            name=op.f("fk_port_source_record_source_version_id_source_version"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_port_source_record")),
        sa.UniqueConstraint(
            "source_version_id",
            "source_record_key",
            name=op.f("uq_port_source_record_version_key"),
        ),
    )
    op.create_index(
        "ix_port_source_record_location",
        "port_source_record",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_port_source_record_un_locode",
        "port_source_record",
        ["un_locode"],
        unique=False,
    )
    op.create_index(
        "ix_port_source_record_country_name",
        "port_source_record",
        ["country_code", "name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_port_source_record_country_name", table_name="port_source_record")
    op.drop_index("ix_port_source_record_un_locode", table_name="port_source_record")
    op.drop_index(
        "ix_port_source_record_location",
        table_name="port_source_record",
        postgresql_using="gist",
    )
    op.drop_table("port_source_record")
