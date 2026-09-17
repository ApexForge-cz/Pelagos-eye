from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from oceanscope_api.ports.contracts import NormalizedPortSourceRecord
from oceanscope_api.ports.models import PortSourceRecord


class SqlAlchemyPortRepository:
    """Persist provider-specific port records without merging source identities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_for_version(self, source_version_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(PortSourceRecord)
            .where(PortSourceRecord.source_version_id == source_version_id)
        )
        return int(self._session.scalar(statement) or 0)

    def replace_version_records(
        self,
        *,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        normalization_version: str,
        records: Sequence[NormalizedPortSourceRecord],
    ) -> None:
        self._session.execute(
            delete(PortSourceRecord).where(PortSourceRecord.source_version_id == source_version_id)
        )
        normalized_at = datetime.now(UTC)
        entities = [
            PortSourceRecord(
                id=uuid4(),
                source_version_id=source_version_id,
                ingestion_run_id=ingestion_run_id,
                source_record_key=record.source_record_key,
                source_record_id=record.source_record_id,
                record_type=record.record_type,
                name=record.name,
                country_code=record.country_code,
                un_locode=record.un_locode,
                longitude=record.longitude,
                latitude=record.latitude,
                location=_location(record),
                coordinate_accuracy=record.coordinate_accuracy,
                function_code=record.function_code,
                source_status=record.source_status,
                source_updated_value=record.source_updated_value,
                normalization_version=normalization_version,
                quality_flags=list(record.quality_flags),
                raw_record=dict(record.raw_record),
                normalized_at=normalized_at,
            )
            for record in records
        ]
        self._session.add_all(entities)
        self._session.flush()


def _location(record: NormalizedPortSourceRecord) -> WKTElement | None:
    if record.longitude is None or record.latitude is None:
        return None
    return WKTElement(f"POINT ({record.longitude} {record.latitude})", srid=4326)
