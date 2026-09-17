from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from oceanscope_api.provenance.models import PublicationStatus, RedistributionStatus


@dataclass(frozen=True)
class SourceDescriptor:
    slug: str
    display_name: str
    official_url: str
    terms_url: str | None
    attribution_text: str
    license_identifier: str | None
    redistribution_status: RedistributionStatus
    terms_reviewed_at: datetime | None


@dataclass(frozen=True)
class FetchedPortDataset:
    source: SourceDescriptor
    data_version: str
    schema_version: str
    source_url: str
    filename: str
    content_type: str | None
    content: bytes
    checksum_sha256: str
    retrieved_at: datetime
    published_at: datetime | None
    publication_status: PublicationStatus = PublicationStatus.PRODUCTION


@dataclass(frozen=True)
class NormalizedPortSourceRecord:
    source_record_key: str
    source_record_id: str
    record_type: str
    name: str
    country_code: str
    un_locode: str | None
    longitude: float | None
    latitude: float | None
    coordinate_accuracy: str | None
    function_code: str | None
    source_status: str | None
    source_updated_value: str | None
    quality_flags: tuple[str, ...] = ()
    raw_record: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PortParseResult:
    records: tuple[NormalizedPortSourceRecord, ...]
    records_received: int
    records_rejected: int
    records_skipped: int
    quality_counts: dict[str, int]


class PortDatasetProvider(Protocol):
    source: SourceDescriptor

    def fetch(self) -> FetchedPortDataset: ...


class PortDatasetParser(Protocol):
    normalization_version: str

    def parse(self, dataset: FetchedPortDataset) -> PortParseResult: ...


class PortDataError(RuntimeError):
    """Base error for official port-reference acquisition and parsing."""


class PortDownloadError(PortDataError):
    """Raised when an official artifact cannot be downloaded safely."""


class PortSchemaError(PortDataError):
    """Raised when an official artifact has an unsupported schema or container."""
