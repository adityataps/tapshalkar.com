import json
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app import core


SAMPLE_GRAPH = {
    "nodes": [{"id": "skill-python", "type": "skill", "label": "Python"}],
    "edges": [],
}


@pytest.mark.anyio
async def test_graph_returns_json():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        return json.dumps(SAMPLE_GRAPH).encode()

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/graph")

    assert response.status_code == 200
    assert response.json()["nodes"][0]["id"] == "skill-python"


@pytest.mark.anyio
async def test_graph_returns_502_on_gcs_error():
    async def mock_fetch_error(_bucket: str, _key: str) -> bytes:
        raise Exception("GCS unavailable")

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch_error):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/graph")

    assert response.status_code == 502
