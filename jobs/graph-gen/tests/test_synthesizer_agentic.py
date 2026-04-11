import json
import pytest
from unittest.mock import MagicMock, patch
from synthesizer import synthesize_graph
from models import GraphOutput, TraktItem, HealthSummary
from sources.github import GitHubData, RepoData
from sources.spotify import SpotifyData, TopArtist, TopTrack, RecentTrack
from sources.steam import SteamData, SteamGame
from sources.trakt import TraktData


SAMPLE_GITHUB = GitHubData(
    repos=[RepoData(name="ml-project", description="ML stuff", languages={"Python": 5000}, stars=3, url="https://github.com/user/ml-project", topics=["ml"])],
    top_languages=["Python"],
)
SAMPLE_SPOTIFY = SpotifyData(
    top_artists=[TopArtist(name="Kendrick Lamar", url="https://open.spotify.com/artist/2YZyLoL8N0Wb9xBt1NhZWg", genres=["hip hop"])],
    top_tracks=[TopTrack(name="HUMBLE.", artist="Kendrick Lamar", url="https://open.spotify.com/track/7KXjTSCq5nL1LoYtL7XAwS")],
    top_genres=["hip hop"],
    recently_played=[],
)
SAMPLE_STEAM = SteamData(
    most_played=[SteamGame(name="Elden Ring", app_id=1245620, hours_played=47, store_url="https://store.steampowered.com/app/1245620")],
    recently_played=[],
)
SAMPLE_TRAKT = TraktData(
    history=[TraktItem(title="Dune: Part Two", year=2024, media_type="movie", trakt_url="https://trakt.tv/movies/dune-part-two-2024", status="watched")],
    watchlist=[],
    watching=None,
)
SAMPLE_HEALTH = HealthSummary(avg_daily_steps=9000, last_workout_type="Running")

MOCK_GRAPH_JSON = {
    "nodes": [{"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}}],
    "edges": [],
}


@pytest.mark.anyio
async def test_synthesize_agentic_returns_graph_output():
    """Synthesizer should handle a single-step loop: Claude calls emit_knowledge_graph directly."""
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "emit_knowledge_graph"
    mock_tool_use.input = MOCK_GRAPH_JSON
    mock_tool_use.id = "tool_1"

    mock_message = MagicMock()
    mock_message.stop_reason = "tool_use"
    mock_message.content = [mock_tool_use]

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(return_value=mock_message)

    with patch("synthesizer.anthropic.Anthropic", return_value=mock_client):
        result = await synthesize_graph(
            github=SAMPLE_GITHUB,
            spotify=SAMPLE_SPOTIFY,
            steam=SAMPLE_STEAM,
            trakt=SAMPLE_TRAKT,
            health=SAMPLE_HEALTH,
            api_key="test-key",
        )

    assert isinstance(result, GraphOutput)
    assert any(n.id == "skill-python" for n in result.nodes)


@pytest.mark.anyio
async def test_synthesize_handles_readme_tool_call():
    """Synthesizer should call fetch_github_readme, then call emit_knowledge_graph on next turn."""
    readme_tool_use = MagicMock()
    readme_tool_use.type = "tool_use"
    readme_tool_use.name = "fetch_github_readme"
    readme_tool_use.input = {"owner": "user", "repo": "ml-project"}
    readme_tool_use.id = "tool_1"

    emit_tool_use = MagicMock()
    emit_tool_use.type = "tool_use"
    emit_tool_use.name = "emit_knowledge_graph"
    emit_tool_use.input = MOCK_GRAPH_JSON
    emit_tool_use.id = "tool_2"

    first_message = MagicMock()
    first_message.stop_reason = "tool_use"
    first_message.content = [readme_tool_use]

    second_message = MagicMock()
    second_message.stop_reason = "tool_use"
    second_message.content = [emit_tool_use]

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(side_effect=[first_message, second_message])

    with patch("synthesizer.anthropic.Anthropic", return_value=mock_client):
        with patch("synthesizer._fetch_readme", return_value="# ML Project\nA machine learning tool."):
            result = await synthesize_graph(
                github=SAMPLE_GITHUB,
                spotify=SAMPLE_SPOTIFY,
                steam=SAMPLE_STEAM,
                trakt=SAMPLE_TRAKT,
                health=SAMPLE_HEALTH,
                api_key="test-key",
            )

    assert isinstance(result, GraphOutput)
    assert mock_client.messages.create.call_count == 2
