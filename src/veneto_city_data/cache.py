from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx


class SourceUnavailableError(RuntimeError):
    """Raised when a source cannot be downloaded and no cache exists."""


@dataclass(frozen=True, slots=True)
class CachedPayload:
    data: bytes
    retrieved_at: datetime
    stale: bool


class FileCache:
    def __init__(self, directory: Path, ttl_seconds: int, timeout_seconds: float) -> None:
        self.directory = directory
        self.ttl = timedelta(seconds=ttl_seconds)
        self.timeout_seconds = timeout_seconds
        self._locks: dict[str, asyncio.Lock] = {}

    async def get(self, key: str, url: str) -> CachedPayload:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            path = self.directory / f"{key}.zip"
            cached = self._read(path)
            if cached and datetime.now(UTC) - cached.retrieved_at <= self.ttl:
                return cached

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds, follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                self.directory.mkdir(parents=True, exist_ok=True)
                temporary_path = path.with_suffix(".tmp")
                temporary_path.write_bytes(response.content)
                temporary_path.replace(path)
                return CachedPayload(response.content, datetime.now(UTC), stale=False)
            except (httpx.HTTPError, OSError) as error:
                if cached:
                    return CachedPayload(cached.data, cached.retrieved_at, stale=True)
                raise SourceUnavailableError(f"The {key} source is unavailable") from error

    @staticmethod
    def _read(path: Path) -> CachedPayload | None:
        try:
            data = path.read_bytes()
            retrieved_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        except FileNotFoundError:
            return None
        return CachedPayload(data, retrieved_at, stale=False)
