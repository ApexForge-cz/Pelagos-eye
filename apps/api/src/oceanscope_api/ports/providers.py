from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from oceanscope_api.ports.contracts import (
    FetchedPortDataset,
    PortDownloadError,
    PortSchemaError,
    SourceDescriptor,
)
from oceanscope_api.ports.download import HttpDownloader
from oceanscope_api.provenance.models import PublicationStatus, RedistributionStatus

UNLOCODE_RELEASE_API = "https://opensource.unicc.org/api/v4/projects/64/releases/permalink/latest"
UNLOCODE_ASSET_NAME = "UNLOCODE Data Archive"
WPI_CSV_URL = "https://msi.nga.mil/api/publications/world-port-index?output=csv"

UNLOCODE_SOURCE = SourceDescriptor(
    slug="unece-unlocode",
    display_name="UNECE UN/LOCODE",
    official_url="https://unlocode.unece.org/publications/",
    terms_url="https://unlocode.unece.org/directory/",
    attribution_text="United Nations Economic Commission for Europe (UNECE) UN/LOCODE",
    license_identifier="CC-BY-4.0",
    redistribution_status=RedistributionStatus.ALLOWED,
    terms_reviewed_at=datetime(2026, 9, 17, tzinfo=UTC),
)

WPI_SOURCE = SourceDescriptor(
    slug="nga-world-port-index",
    display_name="NGA World Port Index",
    official_url="https://msi.nga.mil/Publications/WPI",
    terms_url="https://msi.nga.mil/Publications/WPI",
    attribution_text="National Geospatial-Intelligence Agency (NGA), Maritime Safety Office",
    license_identifier=None,
    redistribution_status=RedistributionStatus.UNREVIEWED,
    terms_reviewed_at=None,
)


class UnLocodeProvider:
    source = UNLOCODE_SOURCE

    def __init__(self, downloader: HttpDownloader) -> None:
        self._downloader = downloader

    def fetch(self) -> FetchedPortDataset:
        metadata_response = self._downloader.get(UNLOCODE_RELEASE_API, max_bytes=2_000_000)
        try:
            metadata = json.loads(metadata_response.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PortSchemaError("UN/LOCODE release metadata is not valid JSON") from error

        tag = _required_text(metadata, "tag_name", "UN/LOCODE release tag")
        released_at = _parse_utc_timestamp(
            _required_text(metadata, "released_at", "UN/LOCODE release time")
        )
        asset_url = _find_release_asset(metadata, UNLOCODE_ASSET_NAME)
        artifact_response = self._downloader.get(asset_url, max_bytes=64_000_000)
        if not artifact_response.content.startswith(b"PK"):
            raise PortSchemaError("UN/LOCODE release artifact is not a ZIP archive")

        content = artifact_response.content
        return FetchedPortDataset(
            source=self.source,
            data_version=tag,
            schema_version="unlocode-publication-csv-12-v1",
            source_url=asset_url,
            filename=f"unlocode-{tag}.zip",
            content_type=artifact_response.content_type,
            content=content,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            retrieved_at=datetime.now(UTC),
            published_at=released_at,
            publication_status=PublicationStatus.PRODUCTION,
        )


class WorldPortIndexProvider:
    source = WPI_SOURCE

    def __init__(self, downloader: HttpDownloader) -> None:
        self._downloader = downloader

    def fetch(self) -> FetchedPortDataset:
        response = self._downloader.get(WPI_CSV_URL, max_bytes=16_000_000)
        content = response.content
        try:
            first_line = content.decode("utf-8-sig").splitlines()[0]
            header = next(csv.reader(io.StringIO(first_line)))
        except (UnicodeDecodeError, IndexError, csv.Error) as error:
            raise PortSchemaError(
                "WPI artifact does not contain a valid UTF-8 CSV header"
            ) from error

        normalized_header = ",".join(column.strip() for column in header)
        schema_hash = hashlib.sha256(normalized_header.encode()).hexdigest()
        content_hash = hashlib.sha256(content).hexdigest()
        return FetchedPortDataset(
            source=self.source,
            data_version=f"sha256:{content_hash}",
            schema_version=f"wpi-header-sha256:{schema_hash}",
            source_url=WPI_CSV_URL,
            filename="world-port-index.csv",
            content_type=response.content_type,
            content=content,
            checksum_sha256=content_hash,
            retrieved_at=datetime.now(UTC),
            published_at=None,
            publication_status=PublicationStatus.PRODUCTION,
        )


def _required_text(document: Any, key: str, label: str) -> str:
    if not isinstance(document, dict):
        raise PortSchemaError("official release metadata must be an object")
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PortSchemaError(f"{label} is missing")
    return value.strip()


def _find_release_asset(document: Any, asset_name: str) -> str:
    if not isinstance(document, dict):
        raise PortSchemaError("official release metadata must be an object")
    assets = document.get("assets")
    links = assets.get("links") if isinstance(assets, dict) else None
    if not isinstance(links, list):
        raise PortSchemaError("UN/LOCODE release asset list is missing")
    for link in links:
        if isinstance(link, dict) and link.get("name") == asset_name:
            url = link.get("direct_asset_url") or link.get("url")
            if isinstance(url, str) and url.startswith("https://opensource.unicc.org/"):
                return url
            raise PortDownloadError("UN/LOCODE release asset URL is not on the official host")
    raise PortSchemaError(f"UN/LOCODE release asset {asset_name!r} is missing")


def _parse_utc_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PortSchemaError("official release timestamp is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PortSchemaError("official release timestamp lacks a timezone")
    return parsed.astimezone(UTC)
