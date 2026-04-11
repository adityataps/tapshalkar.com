import pytest
from unittest.mock import MagicMock, patch
from writer import write_outputs, build_currently
from models import GraphOutput, Node, Edge, ActivityFeed, ActivityItem, NowSnapshot
from sources.github import GitHubData, RepoData
from sources.spotify import SpotifyData, TopArtist, TopTrack, RecentTrack
from sources.steam import SteamData, SteamGame
from sources.trakt import TraktData


GRAPH = GraphOutput(
    nodes=[Node(id="skill-python", type="skill", label="Python")],
    edges=[],
)
FEED = ActivityFeed(items=[ActivityItem(type="commit", title="feat: add thing", subtitle="tapshalkar.com", timestamp="2026-04-09T00:00:00Z")])
NOW = NowSnapshot(current_projects=["tapshalkar.com"], listening_to=["Kendrick Lamar"], recently_played_games=["CS2"], updated_at="2026-04-09T00:00:00Z")


@pytest.mark.anyio
async def test_write_outputs_uploads_four_files():
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    with patch("writer.storage.Client", return_value=mock_client):
        await write_outputs(bucket="test-bucket", graph=GRAPH, feed=FEED, now=NOW, currently={"generated_at": "2026-04-10T00:00:00Z"})

    assert mock_bucket.blob.call_count == 4
    uploaded_keys = {call.args[0] for call in mock_bucket.blob.call_args_list}
    assert uploaded_keys == {"graph.json", "activity-feed.json", "now.json", "currently.json"}


@pytest.mark.anyio
async def test_build_currently_includes_working_on():
    github = GitHubData(
        repos=[
            RepoData(name="tapshalkar.com", description="Portfolio", languages={}, stars=0, url="https://github.com/adityataps/tapshalkar.com", topics=[]),
            RepoData(name="ml-project", description="ML", languages={}, stars=2, url="https://github.com/adityataps/ml-project", topics=[]),
        ],
        top_languages=["Python"],
    )
    spotify = SpotifyData(
        top_artists=[TopArtist(name="Kendrick Lamar", url="https://open.spotify.com/artist/ka", genres=["hip hop"])],
        top_tracks=[TopTrack(name="HUMBLE.", artist="Kendrick Lamar", url="https://open.spotify.com/track/hb")],
        top_genres=["hip hop"],
        recently_played=[RecentTrack(name="HUMBLE.", artist="Kendrick Lamar", played_at="2026-04-09T10:00:00Z", url="https://open.spotify.com/track/hb")],
    )
    steam = SteamData(
        most_played=[SteamGame(name="Elden Ring", app_id=1245620, hours_played=47, store_url="https://store.steampowered.com/app/1245620")],
        recently_played=[],
    )
    trakt = TraktData(history=[], watchlist=[], watching=None)

    result = build_currently(github, spotify, steam, trakt)

    assert "generated_at" in result
    assert len(result["working_on"]) == 2
    assert result["working_on"][0]["name"] == "tapshalkar.com"
    assert result["playing"]["name"] == "Elden Ring"
    assert result["listening_to"]["track"] == "HUMBLE."
    assert result["listening_to"]["url"] == "https://open.spotify.com/track/hb"
