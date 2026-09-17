from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from oceanscope_api.ports.contracts import FetchedPortDataset, PortDataError

SAFE_COMPONENT = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class StoredArtifact:
    reference: str
    checksum_sha256: str
    size_bytes: int


class LocalArtifactStore:
    """Store immutable source artifacts under an ignored runtime data directory."""

    def __init__(self, data_directory: Path) -> None:
        self._root = data_directory / "raw"

    def store(self, dataset: FetchedPortDataset) -> StoredArtifact:
        if not SAFE_COMPONENT.fullmatch(dataset.source.slug):
            raise PortDataError("unsafe source slug for artifact storage")

        checksum = hashlib.sha256(dataset.content).hexdigest()
        if checksum != dataset.checksum_sha256:
            raise PortDataError("artifact checksum changed before storage")

        suffix = Path(dataset.filename).suffix.lower()
        if suffix not in {".csv", ".zip"}:
            raise PortDataError("official artifact must use a supported .csv or .zip suffix")

        target_directory = self._root / dataset.source.slug
        target_directory.mkdir(parents=True, exist_ok=True)
        target = target_directory / f"{checksum}{suffix}"
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
                raise PortDataError("stored artifact checksum does not match its filename")
        else:
            temporary = target_directory / f".{checksum}.{uuid4().hex}.tmp"
            temporary.write_bytes(dataset.content)
            temporary.replace(target)

        return StoredArtifact(
            reference=target.relative_to(self._root.parent).as_posix(),
            checksum_sha256=checksum,
            size_bytes=len(dataset.content),
        )
