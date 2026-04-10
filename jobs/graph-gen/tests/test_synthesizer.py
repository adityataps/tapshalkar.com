import json
import pytest
from unittest.mock import MagicMock, patch
from synthesizer import synthesize_graph
from models import GraphOutput
from sources.github import GitHubData, RepoData
from sources.spotify import SpotifyData, RecentTrack
from sources.steam import SteamData


SAMPLE_GITHUB = GitHubData(
    repos=[RepoData(name="ml-project", description="ML stuff", languages={"Python": 5000}, stars=3, url="", topics=["ml"])],
    top_languages=["Python"],
)
SAMPLE_SPOTIFY = SpotifyData(top_artists=["Kendrick Lamar"], top_tracks=["HUMBLE."], top_genres=["hip hop"], recently_played=[])
SAMPLE_STEAM = SteamData(most_played=["Counter-Strike 2"], recently_played=["Counter-Strike 2"])

MOCK_GRAPH_JSON = {
    "nodes": [
        {"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}},
        {"id": "interest-hip-hop", "type": "interest", "label": "Hip Hop", "description": "", "metadata": {}},
    ],
    "edges": [
        {"source": "skill-python", "target": "skill-python", "type": "relates_to", "weight": 1.0}
    ]
}


@pytest.mark.anyio
async def test_synthesize_returns_graph_output():
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = MOCK_GRAPH_JSON

    mock_message = MagicMock()
    mock_message.content = [mock_tool_use]

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(return_value=mock_message)

    with patch("synthesizer.anthropic.Anthropic", return_value=mock_client):
        result = await synthesize_graph(
            github=SAMPLE_GITHUB,
            spotify=SAMPLE_SPOTIFY,
            steam=SAMPLE_STEAM,
            api_key="test-key",
        )

    assert isinstance(result, GraphOutput)
    assert any(n.id == "skill-python" for n in result.nodes)
    assert len(result.edges) == 1
