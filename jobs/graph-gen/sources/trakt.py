import asyncio
from dataclasses import dataclass, field
import httpx
from models import TraktItem

BASE_URL = "https://api.trakt.tv"


@dataclass
class TraktData:
    history: list[TraktItem]      # recently watched (movies + shows)
    watchlist: list[TraktItem]    # plan to watch
    watching: TraktItem | None    # currently in-progress (may be None)


async def _get_access_token(
    client: httpx.AsyncClient,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    r = await client.post(
        f"{BASE_URL}/oauth/token",
        json={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "refresh_token",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _item_from_movie(movie: dict, status: str) -> TraktItem:
    slug = movie["ids"]["slug"]
    return TraktItem(
        title=movie["title"],
        year=movie.get("year", 0),
        media_type="movie",
        trakt_url=f"https://trakt.tv/movies/{slug}",
        genres=movie.get("genres", []),
        status=status,
    )


def _item_from_show(show: dict, status: str) -> TraktItem:
    slug = show["ids"]["slug"]
    return TraktItem(
        title=show["title"],
        year=show.get("year", 0),
        media_type="show",
        trakt_url=f"https://trakt.tv/shows/{slug}",
        genres=show.get("genres", []),
        status=status,
    )


async def fetch_trakt(client_id: str, client_secret: str, refresh_token: str) -> TraktData:
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_access_token(client, client_id, client_secret, refresh_token)
        headers = {
            "Authorization": f"Bearer {token}",
            "trakt-api-version": "2",
            "trakt-api-key": client_id,
        }

        history_r, watchlist_r = await asyncio.gather(
            client.get(f"{BASE_URL}/users/me/history", headers=headers, params={"limit": 50}),
            client.get(f"{BASE_URL}/users/me/watchlist", headers=headers),
        )
        history_r.raise_for_status()
        watchlist_r.raise_for_status()

        # Currently watching (optional — returns 204 if nothing playing)
        watching_r = await client.get(f"{BASE_URL}/users/me/watching", headers=headers)

    history: list[TraktItem] = []
    seen: set[str] = set()
    for entry in history_r.json():
        if entry["type"] == "movie":
            item = _item_from_movie(entry["movie"], "watched")
        elif entry["type"] == "episode":
            item = _item_from_show(entry["show"], "watched")
        else:
            continue
        key = f"{item.media_type}-{item.title}"
        if key not in seen:
            seen.add(key)
            history.append(item)

    watchlist: list[TraktItem] = []
    for entry in watchlist_r.json():
        if entry["type"] == "movie":
            watchlist.append(_item_from_movie(entry["movie"], "watchlist"))
        elif entry["type"] == "show":
            watchlist.append(_item_from_show(entry["show"], "watchlist"))

    watching: TraktItem | None = None
    if watching_r.status_code == 200:
        w = watching_r.json()
        if w.get("type") == "movie":
            watching = _item_from_movie(w["movie"], "watching")
        elif w.get("type") == "episode":
            watching = _item_from_show(w["show"], "watching")

    return TraktData(history=history, watchlist=watchlist, watching=watching)
