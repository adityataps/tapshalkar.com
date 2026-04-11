import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sources.trakt import fetch_trakt, TraktData


@pytest.mark.anyio
async def test_trakt_returns_history_and_watchlist():
    history_response = [
        {
            "watched_at": "2026-04-01T00:00:00.000Z",
            "type": "movie",
            "movie": {
                "title": "Dune: Part Two",
                "year": 2024,
                "ids": {"trakt": 123, "slug": "dune-part-two-2024"},
                "genres": ["science-fiction"],
            },
        },
        {
            "watched_at": "2026-04-02T00:00:00.000Z",
            "type": "episode",
            "show": {
                "title": "Severance",
                "year": 2022,
                "ids": {"trakt": 456, "slug": "severance"},
                "genres": ["drama"],
            },
            "episode": {"season": 2, "number": 5, "title": "Woe's Hollow"},
        },
    ]
    watchlist_response = [
        {
            "type": "movie",
            "movie": {
                "title": "Conclave",
                "year": 2024,
                "ids": {"trakt": 789, "slug": "conclave-2024"},
                "genres": ["thriller"],
            },
        }
    ]

    with patch("sources.trakt._get_access_token", return_value="fake-token"):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            history_r = MagicMock()
            history_r.json.return_value = history_response
            history_r.raise_for_status = lambda: None

            watchlist_r = MagicMock()
            watchlist_r.json.return_value = watchlist_response
            watchlist_r.raise_for_status = lambda: None

            watching_r = MagicMock()
            watching_r.status_code = 204  # nothing currently playing

            mock_client.get.side_effect = [history_r, watchlist_r, watching_r]

            result = await fetch_trakt(
                client_id="cid",
                client_secret="cs",
                refresh_token="rt",
            )

    assert len(result.history) >= 1
    assert result.history[0].title == "Dune: Part Two"
    assert result.history[0].media_type == "movie"
    assert result.history[0].trakt_url == "https://trakt.tv/movies/dune-part-two-2024"
    assert len(result.watchlist) == 1
    assert result.watchlist[0].title == "Conclave"
    assert result.watching is None
