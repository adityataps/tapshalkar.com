import pytest
import respx
import httpx
from sources.spotify import fetch_spotify, SpotifyData


TOKEN_RESPONSE = {"access_token": "test-access-token", "token_type": "Bearer"}

TOP_ARTISTS_RESPONSE = {
    "items": [
        {
            "name": "Kendrick Lamar",
            "genres": ["hip hop", "rap"],
            "id": "ka123",
            "external_urls": {"spotify": "https://open.spotify.com/artist/2YZyLoL8N0Wb9xBt1NhZWg"},
        },
        {
            "name": "Radiohead",
            "genres": ["alt rock", "art rock"],
            "id": "rh456",
            "external_urls": {"spotify": "https://open.spotify.com/artist/4Z8W4fKeB5YxbusRsdQVPb"},
        },
    ]
}

TOP_TRACKS_RESPONSE = {
    "items": [
        {
            "name": "HUMBLE.",
            "artists": [{"name": "Kendrick Lamar"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/7KXjTSCq5nL1LoYtL7XAwS"},
        },
    ]
}

RECENTLY_PLAYED_RESPONSE = {
    "items": [
        {
            "track": {
                "name": "Creep",
                "artists": [{"name": "Radiohead"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/creep123"},
            },
            "played_at": "2026-04-09T10:00:00Z",
        }
    ]
}


@pytest.mark.anyio
async def test_fetch_spotify_returns_data():
    with respx.mock:
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
            return_value=httpx.Response(200, json=RECENTLY_PLAYED_RESPONSE)
        )

        data = await fetch_spotify(
            client_id="test-id",
            client_secret="test-secret",
            refresh_token="test-refresh",
        )

    assert isinstance(data, SpotifyData)
    assert data.top_artists[0].name == "Kendrick Lamar"
    assert data.top_artists[0].url == "https://open.spotify.com/artist/2YZyLoL8N0Wb9xBt1NhZWg"
    assert data.top_tracks[0].name == "HUMBLE."
    assert data.top_tracks[0].url == "https://open.spotify.com/track/7KXjTSCq5nL1LoYtL7XAwS"
    assert "hip hop" in data.top_genres
    assert len(data.recently_played) == 1
    assert data.recently_played[0].url == "https://open.spotify.com/track/creep123"
