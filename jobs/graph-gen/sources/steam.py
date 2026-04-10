import asyncio
from dataclasses import dataclass
import httpx


@dataclass
class SteamData:
    most_played: list[str]       # top 10 by total hours
    recently_played: list[str]   # played in last 2 weeks


async def fetch_steam(api_key: str, user_id: str) -> SteamData:
    params_base = {"key": api_key, "steamid": user_id, "format": "json"}

    async with httpx.AsyncClient(timeout=30) as client:
        owned_r, recent_r = await asyncio.gather(
            client.get(
                "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
                params={**params_base, "include_appinfo": True},
            ),
            client.get(
                "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/",
                params=params_base,
            ),
        )
        owned_r.raise_for_status()
        recent_r.raise_for_status()

    owned_games = owned_r.json()["response"].get("games", [])
    recent_games = recent_r.json()["response"].get("games", [])

    most_played = [
        g["name"]
        for g in sorted(owned_games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:10]
    ]
    recently_played = [g["name"] for g in recent_games]

    return SteamData(most_played=most_played, recently_played=recently_played)
