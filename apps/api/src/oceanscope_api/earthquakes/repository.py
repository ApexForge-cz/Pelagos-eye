from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from oceanscope_api.earthquakes.contracts import NormalizedEarthquakeEvent
from oceanscope_api.earthquakes.models import EarthquakeEvent


@dataclass(frozen=True)
class EarthquakeUpsertResult:
    inserted: int
    updated: int
    unchanged: int
    stale_revisions: int


class SqlAlchemyEarthquakeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_events(
        self,
        *,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        normalization_version: str,
        records: list[NormalizedEarthquakeEvent],
    ) -> EarthquakeUpsertResult:
        event_ids = [record.event_id for record in records]
        existing = {
            event.event_id: event
            for event in self._session.scalars(
                select(EarthquakeEvent).where(EarthquakeEvent.event_id.in_(event_ids))
            )
        }
        inserted = updated = unchanged = stale = 0
        for record in records:
            current = existing.get(record.event_id)
            if current is None:
                self._session.add(
                    EarthquakeEvent(
                        event_id=record.event_id,
                        source_version_id=source_version_id,
                        ingestion_run_id=ingestion_run_id,
                        normalization_version=normalization_version,
                        **_event_values(record),
                    )
                )
                inserted += 1
            elif record.provider_updated_at > current.provider_updated_at:
                current.source_version_id = source_version_id
                current.ingestion_run_id = ingestion_run_id
                current.normalization_version = normalization_version
                for name, value in _event_values(record).items():
                    setattr(current, name, value)
                updated += 1
            elif record.provider_updated_at == current.provider_updated_at:
                unchanged += 1
            else:
                stale += 1
        self._session.flush()
        return EarthquakeUpsertResult(inserted, updated, unchanged, stale)


def _event_values(record: NormalizedEarthquakeEvent) -> dict[str, object]:
    return {
        "event_time": record.event_time,
        "provider_updated_at": record.provider_updated_at,
        "longitude": record.longitude,
        "latitude": record.latitude,
        "depth_km": record.depth_km,
        "location": WKTElement(f"POINT({record.longitude} {record.latitude})", srid=4326),
        "magnitude": record.magnitude,
        "place": record.place,
        "event_type": record.event_type,
        "provider_status": record.provider_status,
        "tsunami": record.tsunami,
        "significance": record.significance,
        "detail_url": record.detail_url,
        "quality_flags": record.quality_flags,
        "raw_record": record.raw_record,
    }
