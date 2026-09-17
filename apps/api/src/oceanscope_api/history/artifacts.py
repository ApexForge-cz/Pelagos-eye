from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from oceanscope_api.history.contracts import FetchedHistoricalAisArchive, HistoricalAisError


@dataclass(frozen=True)
class StoredHistoricalAisArtifact:
    reference: str
    size_bytes: int


class HistoricalAisArtifactStore:
    def __init__(self, data_directory: Path) -> None:
        self._root = data_directory / "raw" / "noaa-marinecadastre-ais"

    def store(self, archive: FetchedHistoricalAisArchive) -> StoredHistoricalAisArtifact:
        checksum, size_bytes = _hash_file(archive.archive_path)
        if checksum != archive.checksum_sha256 or size_bytes != archive.size_bytes:
            raise HistoricalAisError("MarineCadastre archive changed before storage")
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._root / f"{checksum}.csv.zst"
        if target.exists():
            stored_checksum, stored_size = _hash_file(target)
            if stored_checksum != checksum or stored_size != size_bytes:
                raise HistoricalAisError("stored MarineCadastre artifact checksum mismatch")
        else:
            temporary = self._root / f".{checksum}.{uuid4().hex}.tmp"
            shutil.copyfile(archive.archive_path, temporary)
            temporary.replace(target)
        return StoredHistoricalAisArtifact(
            reference=target.relative_to(self._root.parent.parent).as_posix(),
            size_bytes=size_bytes,
        )


def _hash_file(path: Path) -> tuple[str, int]:
    checksum = hashlib.sha256()
    size_bytes = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
            size_bytes += len(chunk)
    return checksum.hexdigest(), size_bytes
