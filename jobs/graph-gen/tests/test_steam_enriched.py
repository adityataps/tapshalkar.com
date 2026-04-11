import pytest
import respx
import httpx
from sources.steam import fetch_steam, SteamGame


OWNED_GAMES_RESPONSE = {
    "response": {
        "games": [
            {"appid": 1245620, "name": "Elden Ring", "playtime_forever": 2820},
            {"appid": 730, "name": "Counter-Strike 2", "playtime_forever": 1200},
        ]
    }
}

RECENT_GAMES_RESPONSE = {
    "response": {
        "games": [{"appid": 1245620, "name": "Elden Ring", "playtime_2weeks": 300}]
    }
}


@pytest.mark.anyio
async def test_steam_returns_game_objects():
    with respx.mock:
        respx.get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/").mock(
            return_value=httpx.Response(200, json=OWNED_GAMES_RESPONSE)
        )
        respx.get("https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/").mock(
            return_value=httpx.Response(200, json=RECENT_GAMES_RESPONSE)
        )

        result = await fetch_steam(api_key="key", user_id="123")

    assert len(result.most_played) == 2
    assert result.most_played[0].name == "Elden Ring"
    assert result.most_played[0].hours_played == 47  # 2820 min / 60
    assert result.most_played[0].store_url == "https://store.steampowered.com/app/1245620"
    assert result.recently_played[0].name == "Elden Ring"
