import asyncio
import base64
from dataclasses import dataclass, field
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
class SavedShow:
    name: str
    publisher: str
    url: str
    description: str


@dataclass
class SavedAudiobook:
    name: str
    author: str
    url: str


@dataclass
class RecentAlbum:
    name: str
    artist: str
    url: str


@dataclass
class SpotifyData:
    top_artists: list[TopArtist]
    top_tracks: list[TopTrack]
    top_genres: list[str]
    recently_played: list[RecentTrack]
    saved_shows: list[SavedShow] = field(default_factory=list)
    saved_audiobooks: list[SavedAudiobook] = field(default_factory=list)
    recent_albums: list[RecentAlbum] = field(default_factory=list)


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

        artists_r, tracks_r, recent_r, shows_r, audiobooks_r = await asyncio.gather(
            client.get("https://api.spotify.com/v1/me/top/artists", headers=headers, params={"limit": 10, "time_range": "medium_term"}),
            client.get("https://api.spotify.com/v1/me/top/tracks", headers=headers, params={"limit": 10, "time_range": "medium_term"}),
            client.get("https://api.spotify.com/v1/me/player/recently-played", headers=headers, params={"limit": 50}),
            client.get("https://api.spotify.com/v1/me/shows", headers=headers, params={"limit": 10}),
            client.get("https://api.spotify.com/v1/me/audiobooks", headers=headers, params={"limit": 10}),
        )
        artists_r.raise_for_status()
        tracks_r.raise_for_status()
        recent_r.raise_for_status()
        shows_r.raise_for_status()
        audiobooks_r.raise_for_status()

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

    recent_items = recent_r.json()["items"]

    recently_played = [
        RecentTrack(
            name=item["track"]["name"],
            artist=item["track"]["artists"][0]["name"],
            played_at=item["played_at"],
            url=item["track"].get("external_urls", {}).get("spotify", ""),
        )
        for item in recent_items
    ]

    seen_album_ids: set[str] = set()
    recent_albums: list[RecentAlbum] = []
    for item in recent_items:
        album = item["track"].get("album", {})
        album_id = album.get("id")
        if album_id and album_id not in seen_album_ids:
            seen_album_ids.add(album_id)
            album_artists = album.get("artists", [])
            recent_albums.append(RecentAlbum(
                name=album.get("name", ""),
                artist=album_artists[0]["name"] if album_artists else item["track"]["artists"][0]["name"],
                url=album.get("external_urls", {}).get("spotify", ""),
            ))
            if len(recent_albums) >= 10:
                break

    saved_shows = [
        SavedShow(
            name=item["show"]["name"],
            publisher=item["show"]["publisher"],
            url=item["show"]["external_urls"]["spotify"],
            description=item["show"].get("description", "")[:200],
        )
        for item in shows_r.json()["items"]
    ]

    saved_audiobooks = [
        SavedAudiobook(
            name=item["name"],
            author=item["authors"][0]["name"] if item.get("authors") else "",
            url=item.get("external_urls", {}).get("spotify", ""),
        )
        for item in audiobooks_r.json()["items"]
    ]

    return SpotifyData(
        top_artists=top_artists,
        top_tracks=top_tracks,
        top_genres=top_genres,
        recently_played=recently_played,
        saved_shows=saved_shows,
        saved_audiobooks=saved_audiobooks,
        recent_albums=recent_albums,
    )
