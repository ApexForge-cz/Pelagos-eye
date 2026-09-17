from __future__ import annotations

from dataclasses import dataclass

import httpx

from oceanscope_api.ports.contracts import PortDownloadError


@dataclass(frozen=True)
class DownloadResponse:
    url: str
    content_type: str | None
    content: bytes


class HttpDownloader:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        timeout_seconds: float = 60.0,
        user_agent: str = "OceanScope/0.1 official-data-ingestion",
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": user_agent},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get(self, url: str, *, max_bytes: int) -> DownloadResponse:
        try:
            with self._client.stream("GET", url) as response:
                response.raise_for_status()
                declared_length = response.headers.get("content-length")
                if declared_length is not None and int(declared_length) > max_bytes:
                    raise PortDownloadError(
                        f"official artifact exceeds the {max_bytes}-byte download limit"
                    )

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise PortDownloadError(
                            f"official artifact exceeds the {max_bytes}-byte download limit"
                        )
                return DownloadResponse(
                    url=str(response.url),
                    content_type=response.headers.get("content-type"),
                    content=bytes(body),
                )
        except PortDownloadError:
            raise
        except (httpx.HTTPError, ValueError) as error:
            raise PortDownloadError(f"official download failed: {error}") from error

    def __enter__(self) -> HttpDownloader:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
