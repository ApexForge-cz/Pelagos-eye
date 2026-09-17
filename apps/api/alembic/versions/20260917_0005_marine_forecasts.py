"""Add bounded Open-Meteo marine forecast points.

Revision ID: 20260917_0005
Revises: 20260917_0004
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260917_0005"
down_revision: str | Sequence[str] | None = "20260917_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_document = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "marine_forecast_point",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=False),
        sa.Column("requested_latitude", sa.Float(), nullable=False),
        sa.Column("requested_longitude", sa.Float(), nullable=False),
        sa.Column("grid_latitude", sa.Float(), nullable=False),
        sa.Column("grid_longitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("wave_height_m", sa.Float(), nullable=True),
        sa.Column("wave_direction_deg", sa.Float(), nullable=True),
        sa.Column("wave_period_s", sa.Float(), nullable=True),
        sa.Column("sea_surface_temperature_c", sa.Float(), nullable=True),
        sa.Column("ocean_current_velocity_kmh", sa.Float(), nullable=True),
        sa.Column("ocean_current_direction_deg", sa.Float(), nullable=True),
        sa.Column("sea_level_height_msl_m", sa.Float(), nullable=True),
        sa.Column("units", json_document, nullable=False),
        sa.Column("normalization_version", sa.String(length=100), nullable=False),
        sa.Column("quality_flags", json_document, nullable=False),
        sa.Column("raw_record", json_document, nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ocean_current_velocity_kmh IS NULL OR ocean_current_velocity_kmh >= 0",
            name=op.f("ck_marine_forecast_point_current_velocity_nonnegative"),
        ),
        sa.CheckConstraint(
            "grid_latitude BETWEEN -90 AND 90",
            name=op.f("ck_marine_forecast_point_grid_latitude_range"),
        ),
        sa.CheckConstraint(
            "grid_longitude BETWEEN -180 AND 180",
            name=op.f("ck_marine_forecast_point_grid_longitude_range"),
        ),
        sa.CheckConstraint(
            "requested_latitude BETWEEN -90 AND 90",
            name=op.f("ck_marine_forecast_point_requested_latitude_range"),
        ),
        sa.CheckConstraint(
            "requested_longitude BETWEEN -180 AND 180",
            name=op.f("ck_marine_forecast_point_requested_longitude_range"),
        ),
        sa.CheckConstraint(
            "wave_height_m IS NULL OR wave_height_m >= 0",
            name=op.f("ck_marine_forecast_point_wave_height_nonnegative"),
        ),
        sa.CheckConstraint(
            "wave_period_s IS NULL OR wave_period_s >= 0",
            name=op.f("ck_marine_forecast_point_wave_period_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_run.id"],
            name=op.f("fk_marine_forecast_point_ingestion_run_id_ingestion_run"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["source_version.id"],
            name=op.f("fk_marine_forecast_point_source_version_id_source_version"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_marine_forecast_point")),
        sa.UniqueConstraint(
            "source_version_id",
            "request_key",
            "valid_at",
            name="uq_marine_forecast_version_request_time",
        ),
    )
    op.create_index(
        "ix_marine_forecast_location",
        "marine_forecast_point",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_marine_forecast_request_time",
        "marine_forecast_point",
        ["request_key", "valid_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_marine_forecast_request_time", table_name="marine_forecast_point")
    op.drop_index(
        "ix_marine_forecast_location",
        table_name="marine_forecast_point",
        postgresql_using="gist",
    )
    op.drop_table("marine_forecast_point")
