from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from oceanscope_api.history.contracts import NormalizedHistoricalAisPosition
from oceanscope_api.history.models import HistoricalAisPosition


@dataclass(frozen=True)
class HistoricalAisInsertResult:
    inserted: int
    unchanged: int


class SqlAlchemyHistoricalAisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_positions(
        self,
        *,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        request_key: str,
        normalization_version: str,
        records: tuple[NormalizedHistoricalAisPosition, ...],
    ) -> HistoricalAisInsertResult:
        existing: set[str] = set()
        fingerprints = [record.record_fingerprint for record in records]
        for start in range(0, len(fingerprints), 5_000):
            existing.update(
                self._session.scalars(
                    select(HistoricalAisPosition.record_fingerprint).where(
                        HistoricalAisPosition.source_version_id == source_version_id,
                        HistoricalAisPosition.record_fingerprint.in_(
                            fingerprints[start : start + 5_000]
                        ),
                    )
                )
            )
        inserted = 0
        for record in records:
            if record.record_fingerprint in existing:
                continue
            self._session.add(
                HistoricalAisPosition(
                    source_version_id=source_version_id,
                    ingestion_run_id=ingestion_run_id,
                    request_key=request_key,
                    record_fingerprint=record.record_fingerprint,
                    archive_date=record.archive_date,
                    mmsi=record.mmsi,
                    observed_at=record.observed_at,
                    longitude=record.longitude,
                    latitude=record.latitude,
                    location=WKTElement(f"POINT({record.longitude} {record.latitude})", srid=4326),
                    sog_knots=record.sog_knots,
                    cog_deg=record.cog_deg,
                    heading_deg=record.heading_deg,
                    vessel_name=record.vessel_name,
                    imo=record.imo,
                    call_sign=record.call_sign,
                    vessel_type=record.vessel_type,
                    navigation_status=record.navigation_status,
                    length_m=record.length_m,
                    width_m=record.width_m,
                    draft_m=record.draft_m,
                    cargo=record.cargo,
                    transceiver_class=record.transceiver_class,
                    normalization_version=normalization_version,
                    quality_flags=list(record.quality_flags),
                    raw_record=record.raw_record,
                )
            )
            inserted += 1
        self._session.flush()
        return HistoricalAisInsertResult(inserted=inserted, unchanged=len(records) - inserted)
