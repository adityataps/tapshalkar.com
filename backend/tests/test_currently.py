import json
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app import core

SAMPLE_CURRENTLY = {
    "generated_at": "2026-04-10T06:00:00Z",
    "working_on": [{"name": "tapshalkar.com", "url": "https://github.com/adityataps/tapshalkar.com"}],
    "listening_to": {"artist": "Kendrick Lamar", "track": "GNX", "url": "https://open.spotify.com/track/123"},
}


@pytest.mark.anyio
async def test_currently_returns_json():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        return json.dumps(SAMPLE_CURRENTLY).encode()

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/currently")

    assert response.status_code == 200
    assert response.json()["working_on"][0]["name"] == "tapshalkar.com"


@pytest.mark.anyio
async def test_currently_returns_404_when_not_found():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        from google.cloud.exceptions import NotFound
        raise NotFound("currently.json not found")

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/currently")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_currently_returns_502_on_gcs_error():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        raise Exception("GCS unavailable")

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/currently")

    assert response.status_code == 502
