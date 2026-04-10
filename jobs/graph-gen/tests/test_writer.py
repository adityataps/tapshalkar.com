import pytest
from unittest.mock import MagicMock, patch
from writer import write_outputs
from models import GraphOutput, Node, Edge, ActivityFeed, ActivityItem, NowSnapshot


GRAPH = GraphOutput(
    nodes=[Node(id="skill-python", type="skill", label="Python")],
    edges=[],
)
FEED = ActivityFeed(items=[ActivityItem(type="commit", title="feat: add thing", subtitle="tapshalkar.com", timestamp="2026-04-09T00:00:00Z")])
NOW = NowSnapshot(current_projects=["tapshalkar.com"], listening_to=["Kendrick Lamar"], recently_played_games=["CS2"], updated_at="2026-04-09T00:00:00Z")


@pytest.mark.anyio
async def test_write_outputs_uploads_three_files():
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    with patch("writer.storage.Client", return_value=mock_client):
        await write_outputs(bucket="test-bucket", graph=GRAPH, feed=FEED, now=NOW)

    assert mock_bucket.blob.call_count == 3
    uploaded_keys = {call.args[0] for call in mock_bucket.blob.call_args_list}
    assert uploaded_keys == {"graph.json", "activity-feed.json", "now.json"}
