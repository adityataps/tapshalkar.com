import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sources.apple_health import fetch_apple_health


SAMPLE_EXPORT = {
    "data": {
        "metrics": [
            {
                "name": "step_count",
                "units": "count",
                "data": [
                    {"date": "2026-04-08 00:00:00 -0500", "qty": 8500},
                    {"date": "2026-04-09 00:00:00 -0500", "qty": 9200},
                ]
            },
            {
                "name": "active_energy",
                "units": "kcal",
                "data": [
                    {"date": "2026-04-08 00:00:00 -0500", "qty": 450.0},
                    {"date": "2026-04-09 00:00:00 -0500", "qty": 520.0},
                ]
            },
        ],
        "workouts": [
            {
                "name": "Running",
                "duration": 35.0,
                "start": "2026-04-09 07:00:00 -0500",
            }
        ],
    }
}


@pytest.mark.anyio
async def test_apple_health_parses_summary():
    mock_blob = MagicMock()
    mock_blob.download_as_bytes.return_value = json.dumps(SAMPLE_EXPORT).encode()
    mock_blob.updated = "2026-04-09T12:00:00Z"

    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = [mock_blob]
    mock_bucket.blob.return_value = mock_blob

    mock_storage = MagicMock()
    mock_storage.bucket.return_value = mock_bucket

    with patch("sources.apple_health.storage.Client", return_value=mock_storage):
        result = await fetch_apple_health(
            bucket_name="my-bucket",
            prefix="data/ephemeral/apple-health/",
        )

    assert result.avg_daily_steps == 8850
    assert result.last_workout_type == "Running"
    assert result.last_workout_duration_min == 35


@pytest.mark.anyio
async def test_apple_health_returns_empty_when_no_files():
    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = []
    mock_storage = MagicMock()
    mock_storage.bucket.return_value = mock_bucket

    with patch("sources.apple_health.storage.Client", return_value=mock_storage):
        result = await fetch_apple_health(
            bucket_name="my-bucket",
            prefix="data/ephemeral/apple-health/",
        )

    assert result.avg_daily_steps == 0
    assert result.last_workout_type == ""
