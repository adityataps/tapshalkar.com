import json
import pytest
from unittest.mock import MagicMock, patch
from synthesizer import synthesize_graph
from models import GraphOutput, TraktItem, HealthSummary
from sources.github import GitHubData, RepoData
from sources.spotify import SpotifyData, TopArtist, TopTrack, RecentTrack, SavedShow, SavedAudiobook, RecentAlbum
from sources.steam import SteamData, SteamGame
from sources.trakt import TraktData


SAMPLE_GITHUB = GitHubData(
    repos=[RepoData(name="ml-project", description="ML stuff", languages={"Python": 5000}, stars=3, url="", topics=["ml"])],
    top_languages=["Python"],
)
SAMPLE_SPOTIFY = SpotifyData(
    top_artists=[TopArtist(name="Kendrick Lamar", url="https://open.spotify.com/artist/2YZyLoL8N0Wb9xBt1NhZWg", genres=["hip hop"])],
    top_tracks=[TopTrack(name="HUMBLE.", artist="Kendrick Lamar", url="https://open.spotify.com/track/7KXjTSCq5nL1LoYtL7XAwS")],
    top_genres=["hip hop"],
    recently_played=[],
    saved_shows=[SavedShow(name="Lex Fridman Podcast", publisher="Lex Fridman", url="https://open.spotify.com/show/lex1", description="AI and science conversations.")],
    saved_audiobooks=[SavedAudiobook(name="Atomic Habits", author="James Clear", url="https://open.spotify.com/audiobook/ab1")],
    recent_albums=[RecentAlbum(name="DAMN.", artist="Kendrick Lamar", url="https://open.spotify.com/album/damn1")],
)
SAMPLE_STEAM = SteamData(
    most_played=[SteamGame(name="Counter-Strike 2", app_id=730, hours_played=70, store_url="https://store.steampowered.com/app/730")],
    recently_played=[SteamGame(name="Counter-Strike 2", app_id=730, hours_played=70, store_url="https://store.steampowered.com/app/730")],
)
SAMPLE_TRAKT = TraktData(history=[], watchlist=[], watching=None)
SAMPLE_HEALTH = HealthSummary()

MOCK_GRAPH_JSON = {
    "nodes": [
        {"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}},
        {"id": "interest-genre-hip-hop", "type": "interest", "label": "Hip Hop", "description": "", "metadata": {"subtype": "genre"}},
    ],
    "edges": [
        {"source": "skill-python", "target": "interest-genre-hip-hop", "type": "relates_to", "weight": 0.5}
    ]
}


@pytest.mark.anyio
async def test_synthesize_returns_graph_output():
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "emit_knowledge_graph"
    mock_tool_use.input = MOCK_GRAPH_JSON
    mock_tool_use.id = "tool_1"

    mock_message = MagicMock()
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
            bio="test bio",
        )

    assert isinstance(result, GraphOutput)
    assert any(n.id == "skill-python" for n in result.nodes)
    assert len(result.edges) == 1
