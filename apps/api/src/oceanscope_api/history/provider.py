from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from oceanscope_api.history.contracts import (
    FetchedHistoricalAisArchive,
    HistoricalAisDownloadError,
    HistoricalAisRequest,
)
from oceanscope_api.ports.contracts import SourceDescriptor
from oceanscope_api.provenance.models import RedistributionStatus, SourceState

MARINE_CADASTRE_INDEX_URL = "https://noaaocm.blob.core.windows.net/ais/csv2"
MAX_ARCHIVE_BYTES = 350_000_000

MARINE_CADASTRE_SOURCE = SourceDescriptor(
    slug="noaa-marinecadastre-ais",
    display_name="NOAA MarineCadastre Historical AIS",
    official_url="https://marinecadastre.gov/ais/",
    terms_url="https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf",
    attribution_text=(
        "NOAA Office for Coastal Management; U.S. Coast Guard Navigation Center; "
        "Bureau of Ocean Energy Management"
    ),
    license_identifier=None,
    redistribution_status=RedistributionStatus.RESTRICTED,
    terms_reviewed_at=datetime(2026, 9, 17, tzinfo=UTC),
)


class MarineCadastreProvider:
    source = MARINE_CADASTRE_SOURCE

    def __init__(
        self,
        download_directory: Path,
        client: httpx.Client | None = None,
        *,
        timeout_seconds: float = 120.0,
        local_archive: Path | None = None,
    ) -> None:
        self._download_directory = download_directory
        self._local_archive = local_archive
        self._owns_client = client is None
        self._client = client or httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": "OceanScope/0.1 official-data-ingestion"},
        )

    def fetch(self, request: HistoricalAisRequest) -> FetchedHistoricalAisArchive:
        date_value = request.archive_date.isoformat()
        source_url = (
            f"{MARINE_CADASTRE_INDEX_URL}/csv{request.archive_date.year}/ais-{date_value}.csv.zst"
        )
        if self._local_archive is not None:
            return self._from_local_archive(request, source_url)
        self._download_directory.mkdir(parents=True, exist_ok=True)
        target = self._download_directory / f".{date_value}.{uuid4().hex}.csv.zst"
        checksum = hashlib.sha256()
        size_bytes = 0
        try:
            with self._client.stream("GET", source_url) as response:
                response.raise_for_status()
                declared_length = response.headers.get("content-length")
                if declared_length is not None and int(declared_length) > MAX_ARCHIVE_BYTES:
                    raise HistoricalAisDownloadError(
                        f"official archive exceeds the {MAX_ARCHIVE_BYTES}-byte download limit"
                    )
                with target.open("wb") as output:
                    for chunk in response.iter_bytes():
                        size_bytes += len(chunk)
                        if size_bytes > MAX_ARCHIVE_BYTES:
                            raise HistoricalAisDownloadError(
                                "official archive exceeds the bounded download limit"
                            )
                        checksum.update(chunk)
                        output.write(chunk)
        except HistoricalAisDownloadError:
            target.unlink(missing_ok=True)
            raise
        except (httpx.HTTPError, OSError, ValueError) as error:
            target.unlink(missing_ok=True)
            raise HistoricalAisDownloadError(
                f"official MarineCadastre download failed: {error}"
            ) from error
        if size_bytes == 0:
            target.unlink(missing_ok=True)
            raise HistoricalAisDownloadError("official MarineCadastre archive is empty")
        digest = checksum.hexdigest()
        return FetchedHistoricalAisArchive(
            source=self.source,
            request=request,
            data_version=f"{date_value}:sha256:{digest[:16]}",
            schema_version="marinecadastre-csv-2015-2025-v1",
            source_url=source_url,
            archive_path=target,
            checksum_sha256=digest,
            size_bytes=size_bytes,
            retrieved_at=datetime.now(UTC),
        )

    def _from_local_archive(
        self, request: HistoricalAisRequest, source_url: str
    ) -> FetchedHistoricalAisArchive:
        path = self._local_archive
        if path is None or not path.is_file() or path.suffix.lower() != ".zst":
            raise HistoricalAisDownloadError("local archive must be an existing .zst file")
        size_bytes = path.stat().st_size
        if size_bytes == 0 or size_bytes > MAX_ARCHIVE_BYTES:
            raise HistoricalAisDownloadError("local archive size is outside the permitted bounds")
        checksum = hashlib.sha256()
        try:
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    checksum.update(chunk)
        except OSError as error:
            raise HistoricalAisDownloadError(f"local archive could not be read: {error}") from error
        digest = checksum.hexdigest()
        now = datetime.now(UTC)
        cache_age_seconds = max(0, int(now.timestamp() - path.stat().st_mtime))
        return FetchedHistoricalAisArchive(
            source=self.source,
            request=request,
            data_version=f"{request.archive_date.isoformat()}:sha256:{digest[:16]}",
            schema_version="marinecadastre-csv-2015-2025-v1",
            source_url=source_url,
            archive_path=path,
            checksum_sha256=digest,
            size_bytes=size_bytes,
            retrieved_at=now,
            source_state=SourceState.CACHED,
            cache_age_seconds=cache_age_seconds,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> MarineCadastreProvider:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
