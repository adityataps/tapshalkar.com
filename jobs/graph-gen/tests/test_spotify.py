import pytest
import respx
import httpx
from sources.spotify import fetch_spotify, SpotifyData


TOKEN_RESPONSE = {"access_token": "test-access-token", "token_type": "Bearer"}

TOP_ARTISTS_RESPONSE = {
    "items": [
        {"name": "Kendrick Lamar", "genres": ["hip hop", "rap"], "id": "ka123"},
        {"name": "Radiohead", "genres": ["alt rock", "art rock"], "id": "rh456"},
    ]
}

TOP_TRACKS_RESPONSE = {
    "items": [
        {"name": "HUMBLE.", "artists": [{"name": "Kendrick Lamar"}]},
    ]
}

RECENTLY_PLAYED_RESPONSE = {
    "items": [
        {
            "track": {"name": "Creep", "artists": [{"name": "Radiohead"}]},
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
    assert data.top_artists[0] == "Kendrick Lamar"
    assert "hip hop" in data.top_genres
    assert len(data.recently_played) == 1
