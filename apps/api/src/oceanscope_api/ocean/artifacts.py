from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from oceanscope_api.ocean.contracts import FetchedMarineForecast, MarineDataError


@dataclass(frozen=True)
class StoredMarineForecastArtifact:
    reference: str
    size_bytes: int


class MarineForecastArtifactStore:
    def __init__(self, data_directory: Path) -> None:
        self._root = data_directory / "raw" / "open-meteo-marine"

    def store(self, dataset: FetchedMarineForecast) -> StoredMarineForecastArtifact:
        checksum = hashlib.sha256(dataset.content).hexdigest()
        if checksum != dataset.checksum_sha256:
            raise MarineDataError("Open-Meteo artifact checksum changed before storage")
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._root / f"{checksum}.json"
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
                raise MarineDataError("stored Open-Meteo artifact checksum mismatch")
        else:
            temporary = self._root / f".{checksum}.{uuid4().hex}.tmp"
            temporary.write_bytes(dataset.content)
            temporary.replace(target)
        return StoredMarineForecastArtifact(
            reference=target.relative_to(self._root.parent.parent).as_posix(),
            size_bytes=len(dataset.content),
        )
