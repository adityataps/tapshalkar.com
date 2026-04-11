import asyncio
import base64
from dataclasses import dataclass
import httpx


@dataclass
class RecentTrack:
    name: str
    artist: str
    played_at: str
    url: str = ""


@dataclass
class TopArtist:
    name: str
    url: str
    genres: list[str]


@dataclass
class TopTrack:
    name: str
    artist: str
    url: str


@dataclass
class SpotifyData:
    top_artists: list[TopArtist]
    top_tracks: list[TopTrack]
    top_genres: list[str]
    recently_played: list[RecentTrack]


async def _get_access_token(client: httpx.AsyncClient, client_id: str, client_secret: str, refresh_token: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = await client.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {credentials}"},
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def fetch_spotify(client_id: str, client_secret: str, refresh_token: str) -> SpotifyData:
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_access_token(client, client_id, client_secret, refresh_token)
        headers = {"Authorization": f"Bearer {token}"}

        artists_r, tracks_r, recent_r = await asyncio.gather(
            client.get("https://api.spotify.com/v1/me/top/artists", headers=headers, params={"limit": 10, "time_range": "medium_term"}),
            client.get("https://api.spotify.com/v1/me/top/tracks", headers=headers, params={"limit": 10, "time_range": "medium_term"}),
            client.get("https://api.spotify.com/v1/me/player/recently-played", headers=headers, params={"limit": 10}),
        )
        artists_r.raise_for_status()
        tracks_r.raise_for_status()
        recent_r.raise_for_status()

    top_artists = [
        TopArtist(
            name=a["name"],
            url=a["external_urls"]["spotify"],
            genres=a.get("genres", []),
        )
        for a in artists_r.json()["items"]
    ]
    top_tracks = [
        TopTrack(
            name=t["name"],
            artist=t["artists"][0]["name"],
            url=t["external_urls"]["spotify"],
        )
        for t in tracks_r.json()["items"]
    ]

    genre_counts: dict[str, int] = {}
    for artist in top_artists:
        for genre in artist.genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    top_genres = sorted(genre_counts, key=lambda g: genre_counts[g], reverse=True)[:10]

    recently_played = [
        RecentTrack(
            name=item["track"]["name"],
            artist=item["track"]["artists"][0]["name"],
            played_at=item["played_at"],
            url=item["track"].get("external_urls", {}).get("spotify", ""),
        )
        for item in recent_r.json()["items"]
    ]

    return SpotifyData(
        top_artists=top_artists,
        top_tracks=top_tracks,
        top_genres=top_genres,
        recently_played=recently_played,
    )
