import hashlib
import io
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest

from oceanscope_api.ports.artifacts import LocalArtifactStore
from oceanscope_api.ports.contracts import PortDownloadError
from oceanscope_api.ports.download import HttpDownloader
from oceanscope_api.ports.providers import (
    UNLOCODE_RELEASE_API,
    WPI_CSV_URL,
    UnLocodeProvider,
    WorldPortIndexProvider,
)


def test_official_providers_pin_release_or_content_hash() -> None:
    zip_stream = io.BytesIO()
    with ZipFile(zip_stream, "w") as archive:
        archive.writestr(
            "release/csv/UNLOCODE CodeListPart1.csv",
            ",TS,TST,TEST DATA Port,TEST DATA Port,,1-------,AA,2609,,1234N 04530E,",
        )
    archive_bytes = zip_stream.getvalue()
    wpi_bytes = (
        "\ufeffportNumber,portName,countryCode,latitude,longitude,unloCode\n"
        '1,TEST DATA Port,TS,"12°34\'00""N","045°30\'00""E",TS TST\n'
    ).encode()
    asset_url = (
        "https://opensource.unicc.org/un/unece/uncefact/vocab-locode/"
        "-/jobs/artifacts/TEST-DATA/download?job=package-release"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == UNLOCODE_RELEASE_API:
            return httpx.Response(
                200,
                json={
                    "tag_name": "TEST-DATA",
                    "released_at": "2026-09-17T00:00:00Z",
                    "assets": {
                        "links": [
                            {
                                "name": "UNLOCODE Data Archive",
                                "url": asset_url,
                            }
                        ]
                    },
                },
            )
        if str(request.url) == asset_url:
            return httpx.Response(
                200, content=archive_bytes, headers={"content-type": "application/zip"}
            )
        if str(request.url) == WPI_CSV_URL:
            return httpx.Response(
                200,
                content=wpi_bytes,
                headers={"content-type": "application/octet-stream"},
            )
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        downloader = HttpDownloader(client)
        unlocode = UnLocodeProvider(downloader).fetch()
        wpi = WorldPortIndexProvider(downloader).fetch()

    assert unlocode.data_version == "TEST-DATA"
    assert unlocode.checksum_sha256 == hashlib.sha256(archive_bytes).hexdigest()
    assert wpi.data_version == f"sha256:{hashlib.sha256(wpi_bytes).hexdigest()}"
    assert wpi.published_at is None


def test_unlocode_provider_rejects_release_asset_on_unofficial_host() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == UNLOCODE_RELEASE_API
        return httpx.Response(
            200,
            json={
                "tag_name": "TEST-DATA",
                "released_at": "2026-09-17T00:00:00Z",
                "assets": {
                    "links": [
                        {
                            "name": "UNLOCODE Data Archive",
                            "direct_asset_url": "https://example.test/unlocode.zip",
                        }
                    ]
                },
            },
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(PortDownloadError, match="official host"),
    ):
        UnLocodeProvider(HttpDownloader(client)).fetch()


def test_downloader_enforces_bounded_artifact_size() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=b"12345"))
    with (
        httpx.Client(transport=transport) as client,
        pytest.raises(PortDownloadError, match="download limit"),
    ):
        HttpDownloader(client).get("https://example.test/too-large", max_bytes=4)


def test_artifact_store_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    payload = b"TEST DATA artifact"
    from datetime import UTC, datetime

    from oceanscope_api.ports.contracts import FetchedPortDataset
    from oceanscope_api.ports.providers import UNLOCODE_SOURCE

    artifact = FetchedPortDataset(
        source=UNLOCODE_SOURCE,
        data_version="TEST-DATA",
        schema_version="TEST DATA schema",
        source_url="https://example.test/test-data.zip",
        filename="test-data.zip",
        content_type="application/zip",
        content=payload,
        checksum_sha256=hashlib.sha256(payload).hexdigest(),
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
        published_at=None,
    )
    store = LocalArtifactStore(tmp_path)

    first = store.store(artifact)
    second = store.store(artifact)

    assert first == second
    assert first.reference.startswith("raw/unece-unlocode/")
    assert (tmp_path / first.reference).read_bytes() == payload
