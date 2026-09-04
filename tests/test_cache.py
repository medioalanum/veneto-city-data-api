from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx

from veneto_city_data.cache import FileCache, SourceUnavailableError


@respx.mock
async def test_cache_downloads_once_and_reuses_fresh_file(tmp_path: Path) -> None:
    route = respx.get("https://example.test/data.zip").mock(
        return_value=httpx.Response(200, content=b"zip")
    )
    cache = FileCache(tmp_path, ttl_seconds=3600, timeout_seconds=1)

    first, second = await asyncio.gather(
        cache.get("source", "https://example.test/data.zip"),
        cache.get("source", "https://example.test/data.zip"),
    )

    assert route.call_count == 1
    assert first.data == second.data == b"zip"
    assert not first.stale and not second.stale


@respx.mock
async def test_cache_uses_stale_file_when_download_fails(tmp_path: Path) -> None:
    path = tmp_path / "source.zip"
    path.write_bytes(b"old")
    old = datetime.now(UTC) - timedelta(days=2)
    os.utime(path, (old.timestamp(), old.timestamp()))
    respx.get("https://example.test/data.zip").mock(return_value=httpx.Response(503))

    payload = await FileCache(tmp_path, 1, 1).get("source", "https://example.test/data.zip")

    assert payload.data == b"old"
    assert payload.stale


@respx.mock
async def test_cache_raises_without_fallback(tmp_path: Path) -> None:
    respx.get("https://example.test/data.zip").mock(side_effect=httpx.ConnectError("offline"))

    with pytest.raises(SourceUnavailableError):
        await FileCache(tmp_path, 1, 1).get("source", "https://example.test/data.zip")
