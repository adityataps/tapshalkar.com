import asyncio
import base64
from dataclasses import dataclass, field
import httpx


# Artists appearing fewer than this many times in a playlist are excluded
# from the genre API fetch — keeps the distribution meaningful.
GENRE_PLAYLIST_APPEARANCE_THRESHOLD = 5


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
class PlaylistTrack:
    name: str
    artist: str
    added_at: str
    url: str = ""


@dataclass
class PlaylistData:
    id: str
    name: str
    track_count: int
    url: str
    genre_distribution: dict[str, int] = field(default_factory=dict)
    top_genres: list[str] = field(default_factory=list)
    recently_added: list[PlaylistTrack] = field(default_factory=list)


@dataclass
class SpotifyData:
    top_artists: list[TopArtist]
    top_tracks: list[TopTrack]
    top_genres: list[str]
    recently_played: list[RecentTrack]
    saved_shows: list[SavedShow] = field(default_factory=list)
    saved_audiobooks: list[SavedAudiobook] = field(default_factory=list)
    recent_albums: list[RecentAlbum] = field(default_factory=list)
    playlists: list[PlaylistData] = field(default_factory=list)
    artist_play_counts: dict[str, int] = field(default_factory=dict)
    artist_last_played: dict[str, str] = field(default_factory=dict)


async def _get_access_token(client: httpx.AsyncClient, client_id: str, client_secret: str, refresh_token: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = await client.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {credentials}"},
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def _fetch_playlist_info(client: httpx.AsyncClient, headers: dict, playlist_id: str) -> dict:
    r = await client.get(
        f"https://api.spotify.com/v1/playlists/{playlist_id}",
        headers=headers,
        params={"fields": "id,name,tracks(total),external_urls"},
    )
    r.raise_for_status()
    data = r.json()
    return {
        "id": data.get("id", playlist_id),
        "name": data.get("name", ""),
        "track_count": data.get("tracks", {}).get("total", 0),
        "url": data.get("external_urls", {}).get("spotify", ""),
    }


async def _fetch_playlist_genres(
    client: httpx.AsyncClient,
    headers: dict,
    playlist_id: str,
    min_appearances: int = GENRE_PLAYLIST_APPEARANCE_THRESHOLD,
) -> dict[str, int]:
    """
    Paginate playlist tracks (up to 500), count artist appearances, then
    batch-fetch genres only for artists meeting the appearance threshold.
    """
    artist_counts: dict[str, int] = {}
    offset = 0
    max_tracks = 500

    while offset < max_tracks:
        r = await client.get(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers=headers,
            params={
                "fields": "items(track(artists(id,name))),next",
                "limit": 100,
                "offset": offset,
            },
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            track = item.get("track") or {}
            for artist in track.get("artists", []):
                aid = artist.get("id")
                if aid:
                    artist_counts[aid] = artist_counts.get(aid, 0) + 1

        offset += 100
        if not data.get("next"):
            break

    qualifying_ids = [
        aid for aid, count in artist_counts.items()
        if count >= min_appearances
    ]
    if not qualifying_ids:
        return {}

    genre_counts: dict[str, int] = {}
    for i in range(0, len(qualifying_ids), 50):
        batch = qualifying_ids[i : i + 50]
        r = await client.get(
            "https://api.spotify.com/v1/artists",
            headers=headers,
            params={"ids": ",".join(batch)},
        )
        r.raise_for_status()
        for artist in r.json().get("artists", []) or []:
            if artist:
                for genre in artist.get("genres", []):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1

    return genre_counts


async def _fetch_playlist_recent_tracks(
    client: httpx.AsyncClient,
    headers: dict,
    playlist_id: str,
    limit: int = 20,
) -> list[PlaylistTrack]:
    r = await client.get(
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
        headers=headers,
        params={
            "fields": "items(added_at,track(name,artists(name),external_urls))",
            "limit": limit,
            "offset": 0,
        },
    )
    r.raise_for_status()
    tracks = []
    for item in r.json().get("items", []):
        track = item.get("track") or {}
        artists = track.get("artists", [])
        tracks.append(PlaylistTrack(
            name=track.get("name", ""),
            artist=artists[0]["name"] if artists else "",
            added_at=item.get("added_at", ""),
            url=track.get("external_urls", {}).get("spotify", ""),
        ))
    return tracks


async def fetch_spotify(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    playlist_ids: list[str] | None = None,
) -> SpotifyData:
    async with httpx.AsyncClient(timeout=60) as client:
        token = await _get_access_token(client, client_id, client_secret, refresh_token)
        headers = {"Authorization": f"Bearer {token}"}

        artists_r, tracks_r, recent_r, shows_r, audiobooks_r = await asyncio.gather(
            client.get("https://api.spotify.com/v1/me/top/artists", headers=headers, params={"limit": 10, "time_range": "medium_term"}),
            client.get("https://api.spotify.com/v1/me/top/tracks", headers=headers, params={"limit": 10, "time_range": "medium_term"}),
            client.get("https://api.spotify.com/v1/me/player/recently-played", headers=headers, params={"limit": 50}),
            client.get("https://api.spotify.com/v1/me/shows", headers=headers, params={"limit": 10}),
            client.get("https://api.spotify.com/v1/me/audiobooks", headers=headers, params={"limit": 10}),
        )
        for r in [artists_r, tracks_r, recent_r, shows_r, audiobooks_r]:
            r.raise_for_status()

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

        # Derive per-artist play counts and recency from recently_played (no extra API calls)
        artist_play_counts: dict[str, int] = {}
        artist_last_played: dict[str, str] = {}
        for item in recent_items:
            name = item["track"]["artists"][0]["name"]
            played_at = item["played_at"]
            artist_play_counts[name] = artist_play_counts.get(name, 0) + 1
            if name not in artist_last_played or played_at > artist_last_played[name]:
                artist_last_played[name] = played_at

        # Fetch configured playlists
        playlists: list[PlaylistData] = []
        for pid in (playlist_ids or []):
            try:
                info = await _fetch_playlist_info(client, headers, pid)
                genre_dist, recent_tracks = await asyncio.gather(
                    _fetch_playlist_genres(client, headers, pid),
                    _fetch_playlist_recent_tracks(client, headers, pid),
                )
                top_genres_pl = sorted(genre_dist, key=lambda g: genre_dist[g], reverse=True)[:10]
                playlists.append(PlaylistData(
                    id=info["id"],
                    name=info["name"],
                    track_count=info["track_count"],
                    url=info["url"],
                    genre_distribution=genre_dist,
                    top_genres=top_genres_pl,
                    recently_added=recent_tracks,
                ))
                print(f"  Playlist '{info['name']}': {info['track_count']} tracks, "
                      f"{len(genre_dist)} genres, {len(recent_tracks)} recent additions")
            except Exception as e:
                print(f"  Warning: failed to fetch playlist {pid}: {e}")

    return SpotifyData(
        top_artists=top_artists,
        top_tracks=top_tracks,
        top_genres=top_genres,
        recently_played=recently_played,
        saved_shows=saved_shows,
        saved_audiobooks=saved_audiobooks,
        recent_albums=recent_albums,
        playlists=playlists,
        artist_play_counts=artist_play_counts,
        artist_last_played=artist_last_played,
    )
