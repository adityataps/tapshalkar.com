import pytest
import respx
import httpx
from sources.steam import fetch_steam, SteamData


OWNED_GAMES_RESPONSE = {
    "response": {
        "games": [
            {"appid": 730, "name": "Counter-Strike 2", "playtime_forever": 4200},
            {"appid": 570, "name": "Dota 2", "playtime_forever": 100},
        ]
    }
}

RECENT_GAMES_RESPONSE = {
    "response": {
        "games": [
            {"appid": 730, "name": "Counter-Strike 2", "playtime_2weeks": 300},
        ]
    }
}


@pytest.mark.anyio
async def test_fetch_steam_returns_data():
    with respx.mock:
        respx.get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/").mock(
            return_value=httpx.Response(200, json=OWNED_GAMES_RESPONSE)
        )
        respx.get("https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/").mock(
            return_value=httpx.Response(200, json=RECENT_GAMES_RESPONSE)
        )

        data = await fetch_steam(api_key="test-key", user_id="76561198000000000")

    assert isinstance(data, SteamData)
    assert data.most_played[0] == "Counter-Strike 2"
    assert len(data.recently_played) == 1
