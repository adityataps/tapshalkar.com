import pytest
import respx
import httpx
from sources.spotify import fetch_spotify, SpotifyData

TOKEN_RESPONSE = {"access_token": "test-access-token", "token_type": "Bearer"}
TOP_ARTISTS_RESPONSE = {"items": [{"name": "Kendrick Lamar", "genres": ["hip hop"], "id": "ka1", "external_urls": {"spotify": "https://open.spotify.com/artist/ka1"}}]}
TOP_TRACKS_RESPONSE = {"items": [{"name": "HUMBLE.", "artists": [{"name": "Kendrick Lamar"}], "external_urls": {"spotify": "https://open.spotify.com/track/hb1"}}]}
RECENTLY_PLAYED_RESPONSE = {
    "items": [
        {
            "track": {
                "name": "HUMBLE.",
                "artists": [{"name": "Kendrick Lamar"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/hb1"},
                "album": {"id": "alb1", "name": "DAMN.", "external_urls": {"spotify": "https://open.spotify.com/album/alb1"}},
            },
            "played_at": "2026-04-09T10:00:00Z",
        },
        {
            "track": {
                "name": "Creep",
                "artists": [{"name": "Radiohead"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/creep1"},
                "album": {"id": "alb2", "name": "Pablo Honey", "external_urls": {"spotify": "https://open.spotify.com/album/alb2"}},
            },
            "played_at": "2026-04-09T09:00:00Z",
        },
        {
            "track": {
                "name": "DNA.",
                "artists": [{"name": "Kendrick Lamar"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/dna1"},
                "album": {"id": "alb1", "name": "DAMN.", "external_urls": {"spotify": "https://open.spotify.com/album/alb1"}},
            },
            "played_at": "2026-04-09T08:00:00Z",
        },
    ]
}
SHOWS_RESPONSE = {
    "items": [
        {
            "show": {
                "name": "Lex Fridman Podcast",
                "publisher": "Lex Fridman",
                "external_urls": {"spotify": "https://open.spotify.com/show/lex1"},
                "description": "Conversations about science and technology.",
            }
        }
    ]
}
AUDIOBOOKS_RESPONSE = {
    "items": [
        {
            "name": "Atomic Habits",
            "authors": [{"name": "James Clear"}],
            "external_urls": {"spotify": "https://open.spotify.com/audiobook/ab1"},
        }
    ]
}


def _mock_all(recently_played=None, shows=None, audiobooks=None):
    """Helper: registers all 5 endpoint mocks."""
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(200, json=TOKEN_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/top/artists").mock(
        return_value=httpx.Response(200, json=TOP_ARTISTS_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/top/tracks").mock(
        return_value=httpx.Response(200, json=TOP_TRACKS_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/player/recently-played").mock(
        return_value=httpx.Response(200, json=recently_played or RECENTLY_PLAYED_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/shows").mock(
        return_value=httpx.Response(200, json=shows or SHOWS_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/audiobooks").mock(
        return_value=httpx.Response(200, json=audiobooks or AUDIOBOOKS_RESPONSE)
    )


@pytest.mark.anyio
async def test_fetch_spotify_includes_saved_shows():
    with respx.mock:
        _mock_all()
        data = await fetch_spotify(client_id="id", client_secret="secret", refresh_token="token")

    assert len(data.saved_shows) == 1
    assert data.saved_shows[0].name == "Lex Fridman Podcast"
    assert data.saved_shows[0].publisher == "Lex Fridman"
    assert data.saved_shows[0].url == "https://open.spotify.com/show/lex1"
    assert "science" in data.saved_shows[0].description


@pytest.mark.anyio
async def test_fetch_spotify_includes_audiobooks():
    with respx.mock:
        _mock_all()
        data = await fetch_spotify(client_id="id", client_secret="secret", refresh_token="token")

    assert len(data.saved_audiobooks) == 1
    assert data.saved_audiobooks[0].name == "Atomic Habits"
    assert data.saved_audiobooks[0].author == "James Clear"
    assert data.saved_audiobooks[0].url == "https://open.spotify.com/audiobook/ab1"


@pytest.mark.anyio
async def test_fetch_spotify_extracts_recent_albums_deduped():
    with respx.mock:
        _mock_all()
        data = await fetch_spotify(client_id="id", client_secret="secret", refresh_token="token")

    # 3 tracks across 2 albums — DAMN. appears twice but should be deduped
    assert len(data.recent_albums) == 2
    names = [a.name for a in data.recent_albums]
    assert "DAMN." in names
    assert "Pablo Honey" in names
    assert data.recent_albums[0].url == "https://open.spotify.com/album/alb1"
