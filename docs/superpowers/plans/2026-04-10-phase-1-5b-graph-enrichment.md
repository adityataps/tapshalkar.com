# Phase 1.5B — Graph Enrichment & Agentic Synthesizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the knowledge graph with metadata (URLs, stats, achievements), add Trakt.tv and Apple Health data sources, rewrite the synthesizer as an agentic Claude tool-use loop, and write `currently.json` to GCS.

**Architecture:** Two new source modules (`sources/trakt.py`, `sources/apple_health.py`). Existing sources enriched with URL/stats metadata. Synthesizer rewritten as a tool-use loop: Claude calls `fetch_github_readme` for context enrichment, then calls `emit_knowledge_graph` to terminate. `writer.py` gains `currently.json` output built from gathered data. Infra gains Trakt secrets and a GCS lifecycle rule on the `data/ephemeral/` prefix.

**Tech Stack:** Python 3.13, httpx, anthropic, google-cloud-storage, uv, pytest

**Prerequisites:**
- Phase 1 graph-gen complete
- Trakt.tv app created at trakt.tv/oauth/applications (client_id + client_secret in hand)
- Health Auto Export iOS app configured to export to `gs://adits-gcp-static-site/data/ephemeral/apple-health/`

---

## File Map

```
jobs/graph-gen/
├── sources/
│   ├── github.py          # No changes needed — RepoData.url already populated
│   ├── spotify.py         # Add artist_urls, track_urls to SpotifyData
│   ├── steam.py           # Add SteamGame dataclass with app_id, hours, store_url
│   ├── trakt.py           # New: OAuth + history/watchlist/currently-watching
│   └── apple_health.py    # New: reads latest JSON from GCS prefix
├── synthesizer.py         # Rewrite: agentic loop with fetch_github_readme tool
├── writer.py              # Add currently.json output
├── main.py                # Add Trakt + Apple Health; build currently.json data
└── models.py              # Add TraktItem, HealthSummary dataclasses

infra/
├── gcs.tf                 # Add lifecycle rule for data/ephemeral/ prefix
├── secrets.tf             # Add trakt-client-id, trakt-client-secret, trakt-refresh-token
└── cloud_run_job.tf       # Wire Trakt secrets into job env
```

---

## Task 1: Infra — Trakt Secrets + GCS Lifecycle Rule

- [ ] **Step 1: Add Trakt secrets to `infra/secrets.tf`**

Read the file first. Add `"trakt-client-id"`, `"trakt-client-secret"`, `"trakt-refresh-token"` to the `secret_ids` local and to the `graph_gen_secrets` IAM set:

```hcl
locals {
  secret_ids = [
    "anthropic-api-key",
    "spotify-client-id",
    "spotify-client-secret",
    "spotify-refresh-token",
    "steam-api-key",
    "github-token",
    "resend-api-key",
    "trakt-client-id",
    "trakt-client-secret",
    "trakt-refresh-token",
  ]
}
```

Update `graph_gen_secrets` for_each to include the three trakt secrets:

```hcl
resource "google_secret_manager_secret_iam_member" "graph_gen_secrets" {
  for_each = toset([
    "anthropic-api-key",
    "spotify-client-id",
    "spotify-client-secret",
    "spotify-refresh-token",
    "steam-api-key",
    "github-token",
    "trakt-client-id",
    "trakt-client-secret",
    "trakt-refresh-token",
  ])
  ...
}
```

- [ ] **Step 2: Add GCS lifecycle rule to `infra/gcs.tf`**

Read the file first. Add a `lifecycle_rule` block to `google_storage_bucket.static_site`:

```hcl
lifecycle_rule {
  condition {
    days_since_noncurrent_time = 365
    matches_prefix             = ["data/ephemeral/"]
  }
  action {
    type = "Delete"
  }
}
```

- [ ] **Step 3: Wire Trakt secrets into Cloud Run job in `infra/cloud_run_job.tf`**

Read the file first. Add three entries to the `for_each` map in the dynamic `env` block:

```hcl
"TRAKT_CLIENT_ID"     = "trakt-client-id"
"TRAKT_CLIENT_SECRET" = "trakt-client-secret"
"TRAKT_REFRESH_TOKEN" = "trakt-refresh-token"
```

- [ ] **Step 4: Terraform apply**

```bash
cd infra
terraform apply
```

Expected: 3 new secrets created, bucket lifecycle rule added, Cloud Run job updated.

- [ ] **Step 5: Add secret values to Secret Manager**

```bash
echo -n "YOUR_TRAKT_CLIENT_ID" | gcloud secrets versions add trakt-client-id --data-file=-
echo -n "YOUR_TRAKT_CLIENT_SECRET" | gcloud secrets versions add trakt-client-secret --data-file=-
# trakt-refresh-token added after OAuth flow in Task 3
```

- [ ] **Step 6: Commit infra changes**

```bash
git add infra/
git commit -m "feat(infra): trakt secrets, GCS ephemeral lifecycle rule"
```

---

## Task 2: Enrich Existing Sources

### Steam — add app_id, hours_played, store_url

- [ ] **Step 1: Write failing test `jobs/graph-gen/tests/test_steam_enriched.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from sources.steam import fetch_steam, SteamGame


@pytest.mark.anyio
async def test_steam_returns_game_objects():
    owned_response = {
        "response": {
            "games": [
                {"appid": 1245620, "name": "Elden Ring", "playtime_forever": 2820},
                {"appid": 730, "name": "Counter-Strike 2", "playtime_forever": 1200},
            ]
        }
    }
    recent_response = {
        "response": {
            "games": [{"appid": 1245620, "name": "Elden Ring", "playtime_2weeks": 300}]
        }
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        owned_r = AsyncMock()
        owned_r.json.return_value = owned_response
        owned_r.raise_for_status = lambda: None

        recent_r = AsyncMock()
        recent_r.json.return_value = recent_response
        recent_r.raise_for_status = lambda: None

        mock_client.get.side_effect = [owned_r, recent_r]

        result = await fetch_steam(api_key="key", user_id="123")

    assert len(result.most_played) == 2
    assert result.most_played[0].name == "Elden Ring"
    assert result.most_played[0].hours_played == 47  # 2820 min / 60
    assert result.most_played[0].store_url == "https://store.steampowered.com/app/1245620"
    assert result.recently_played[0].name == "Elden Ring"
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd jobs/graph-gen
uv run pytest tests/test_steam_enriched.py -v
```

Expected: FAILED — `SteamGame` not defined

- [ ] **Step 3: Update `jobs/graph-gen/sources/steam.py`**

```python
import asyncio
from dataclasses import dataclass
import httpx


@dataclass
class SteamGame:
    name: str
    app_id: int
    hours_played: int        # total hours (converted from minutes)
    store_url: str


@dataclass
class SteamData:
    most_played: list[SteamGame]      # top 10 by total hours
    recently_played: list[SteamGame]  # played in last 2 weeks


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

    def _to_game(g: dict) -> SteamGame:
        return SteamGame(
            name=g["name"],
            app_id=g["appid"],
            hours_played=g.get("playtime_forever", 0) // 60,
            store_url=f"https://store.steampowered.com/app/{g['appid']}",
        )

    owned_games = owned_r.json()["response"].get("games", [])
    recent_games = recent_r.json()["response"].get("games", [])

    most_played = [
        _to_game(g)
        for g in sorted(owned_games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:10]
    ]
    recently_played = [_to_game(g) for g in recent_games]

    return SteamData(most_played=most_played, recently_played=recently_played)
```

- [ ] **Step 4: Run test — verify it passes**

```bash
uv run pytest tests/test_steam_enriched.py -v
```

Expected: PASSED

### Spotify — add artist_urls, track_url to top track

- [ ] **Step 5: Update `jobs/graph-gen/sources/spotify.py`**

Read the file. Update `SpotifyData` and `fetch_spotify` to capture the top track's Spotify URL and top artist URLs:

```python
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
```

Update `fetch_spotify` to build `TopArtist` and `TopTrack` objects:

```python
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
```

- [ ] **Step 6: Run existing Spotify test — verify it still passes**

```bash
uv run pytest tests/test_spotify.py -v
```

If the test uses `top_artists: list[str]`, update the test fixture to use `TopArtist` objects. The test should pass.

- [ ] **Step 7: Run all existing tests**

```bash
uv run pytest -v
```

Fix any failures caused by the Steam/Spotify dataclass changes (update fixtures in `test_synthesizer.py` and `test_writer.py` if they reference old field types).

- [ ] **Step 8: Commit**

```bash
git add jobs/graph-gen/sources/steam.py jobs/graph-gen/sources/spotify.py jobs/graph-gen/tests/
git commit -m "feat(graph-gen): enrich steam and spotify sources with URLs and metadata"
```

---

## Task 3: Trakt.tv Gatherer

- [ ] **Step 1: Get Trakt refresh token via OAuth**

Build the auth URL and open in browser:
```
https://trakt.tv/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob
```

Trakt shows a PIN code — exchange it:

```bash
curl -X POST https://api.trakt.tv/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "code": "YOUR_PIN",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
    "grant_type": "authorization_code"
  }'
```

Store the `refresh_token`:

```bash
echo -n "YOUR_REFRESH_TOKEN" | gcloud secrets versions add trakt-refresh-token --data-file=-
```

- [ ] **Step 2: Add `TraktItem` to `jobs/graph-gen/models.py`**

Read `models.py`. Append:

```python
@dataclass
class TraktItem:
    title: str
    year: int
    media_type: str    # "movie" or "show"
    trakt_url: str
    genres: list[str] = field(default_factory=list)
    status: str = ""   # "watched" | "watching" | "watchlist"
```

- [ ] **Step 3: Write failing test `jobs/graph-gen/tests/test_trakt.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch
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

            history_r = AsyncMock()
            history_r.json.return_value = history_response
            history_r.raise_for_status = lambda: None

            watchlist_r = AsyncMock()
            watchlist_r.json.return_value = watchlist_response
            watchlist_r.raise_for_status = lambda: None

            mock_client.get.side_effect = [history_r, watchlist_r]

            result = await fetch_trakt(
                client_id="cid",
                client_secret="cs",
                refresh_token="rt",
            )

    assert len(result.history) >= 1
    assert result.history[0].title == "Dune: Part Two"
    assert result.history[0].media_type == "movie"
    assert len(result.watchlist) == 1
    assert result.watchlist[0].title == "Conclave"
```

- [ ] **Step 4: Run test — verify it fails**

```bash
uv run pytest tests/test_trakt.py -v
```

Expected: FAILED — `sources.trakt` not found

- [ ] **Step 5: Create `jobs/graph-gen/sources/trakt.py`**

```python
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
```

- [ ] **Step 6: Run test — verify it passes**

```bash
uv run pytest tests/test_trakt.py -v
```

Expected: PASSED

- [ ] **Step 7: Commit**

```bash
git add jobs/graph-gen/sources/trakt.py jobs/graph-gen/tests/test_trakt.py jobs/graph-gen/models.py
git commit -m "feat(graph-gen): trakt.tv gatherer"
```

---

## Task 4: Apple Health Gatherer

- [ ] **Step 1: Add `HealthSummary` to `jobs/graph-gen/models.py`**

Read the file. Append:

```python
@dataclass
class HealthSummary:
    avg_daily_steps: int = 0
    avg_active_energy_kcal: float = 0.0
    avg_sleep_hours: float = 0.0
    last_workout_type: str = ""
    last_workout_duration_min: int = 0
    data_through: str = ""   # ISO date of most recent record
```

- [ ] **Step 2: Write failing test `jobs/graph-gen/tests/test_apple_health.py`**

```python
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sources.apple_health import fetch_apple_health


SAMPLE_EXPORT = {
    "data": {
        "metrics": [
            {
                "name": "step_count",
                "units": "count",
                "data": [
                    {"date": "2026-04-08 00:00:00 -0500", "qty": 8500},
                    {"date": "2026-04-09 00:00:00 -0500", "qty": 9200},
                ]
            },
            {
                "name": "active_energy",
                "units": "kcal",
                "data": [
                    {"date": "2026-04-08 00:00:00 -0500", "qty": 450.0},
                    {"date": "2026-04-09 00:00:00 -0500", "qty": 520.0},
                ]
            },
        ],
        "workouts": [
            {
                "name": "Running",
                "duration": 35.0,
                "start": "2026-04-09 07:00:00 -0500",
            }
        ],
    }
}


@pytest.mark.anyio
async def test_apple_health_parses_summary():
    mock_blob = MagicMock()
    mock_blob.download_as_bytes.return_value = json.dumps(SAMPLE_EXPORT).encode()

    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = [mock_blob]
    mock_bucket.blob.return_value = mock_blob

    mock_storage = MagicMock()
    mock_storage.bucket.return_value = mock_bucket

    with patch("sources.apple_health.storage.Client", return_value=mock_storage):
        result = await fetch_apple_health(
            bucket_name="my-bucket",
            prefix="data/ephemeral/apple-health/",
        )

    assert result.avg_daily_steps == 8850
    assert result.last_workout_type == "Running"
    assert result.last_workout_duration_min == 35


@pytest.mark.anyio
async def test_apple_health_returns_empty_when_no_files():
    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = []
    mock_storage = MagicMock()
    mock_storage.bucket.return_value = mock_bucket

    with patch("sources.apple_health.storage.Client", return_value=mock_storage):
        result = await fetch_apple_health(
            bucket_name="my-bucket",
            prefix="data/ephemeral/apple-health/",
        )

    assert result.avg_daily_steps == 0
    assert result.last_workout_type == ""
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
uv run pytest tests/test_apple_health.py -v
```

Expected: FAILED — `sources.apple_health` not found

- [ ] **Step 4: Create `jobs/graph-gen/sources/apple_health.py`**

```python
import asyncio
import json
from google.cloud import storage
from models import HealthSummary


def _sync_fetch(bucket_name: str, prefix: str) -> HealthSummary:
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blobs = list(bucket.list_blobs(prefix=prefix))
    if not blobs:
        return HealthSummary()

    # Use the most recently updated file
    latest = max(blobs, key=lambda b: b.updated)
    raw = json.loads(latest.download_as_bytes())

    # Health Auto Export format: {"data": {"metrics": [...], "workouts": [...]}}
    data = raw.get("data", raw)  # handle both wrapped and unwrapped formats
    metrics = {m["name"]: m.get("data", []) for m in data.get("metrics", [])}
    workouts = data.get("workouts", [])

    def _avg(records: list[dict]) -> float:
        vals = [r["qty"] for r in records if "qty" in r]
        return sum(vals) / len(vals) if vals else 0.0

    steps = metrics.get("step_count", [])
    energy = metrics.get("active_energy", [])
    sleep = metrics.get("sleep_analysis", [])

    last_workout_type = ""
    last_workout_duration_min = 0
    if workouts:
        last = sorted(workouts, key=lambda w: w.get("start", ""), reverse=True)[0]
        last_workout_type = last.get("name", "")
        last_workout_duration_min = int(last.get("duration", 0))

    data_through = ""
    all_dates = [r.get("date", "") for records in metrics.values() for r in records]
    if all_dates:
        data_through = sorted(all_dates)[-1]

    return HealthSummary(
        avg_daily_steps=int(_avg(steps)),
        avg_active_energy_kcal=round(_avg(energy), 1),
        avg_sleep_hours=round(_avg(sleep), 1),
        last_workout_type=last_workout_type,
        last_workout_duration_min=last_workout_duration_min,
        data_through=data_through,
    )


async def fetch_apple_health(bucket_name: str, prefix: str) -> HealthSummary:
    return await asyncio.to_thread(_sync_fetch, bucket_name, prefix)
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
uv run pytest tests/test_apple_health.py -v
```

Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add jobs/graph-gen/sources/apple_health.py jobs/graph-gen/tests/test_apple_health.py jobs/graph-gen/models.py
git commit -m "feat(graph-gen): apple health gatherer from GCS prefix"
```

---

## Task 5: Agentic Synthesizer

- [ ] **Step 1: Write failing test `jobs/graph-gen/tests/test_synthesizer_agentic.py`**

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from synthesizer import synthesize_graph
from models import GraphOutput, TraktItem, HealthSummary
from sources.github import GitHubData, RepoData
from sources.spotify import SpotifyData, TopArtist, TopTrack, RecentTrack
from sources.steam import SteamData, SteamGame
from sources.trakt import TraktData


SAMPLE_GITHUB = GitHubData(
    repos=[RepoData(name="ml-project", description="ML stuff", languages={"Python": 5000}, stars=3, url="https://github.com/user/ml-project", topics=["ml"])],
    top_languages=["Python"],
)
SAMPLE_SPOTIFY = SpotifyData(
    top_artists=[TopArtist(name="Kendrick Lamar", url="https://open.spotify.com/artist/2YZyLoL8N0Wb9xBt1NhZWg", genres=["hip hop"])],
    top_tracks=[TopTrack(name="HUMBLE.", artist="Kendrick Lamar", url="https://open.spotify.com/track/7KXjTSCq5nL1LoYtL7XAwS")],
    top_genres=["hip hop"],
    recently_played=[],
)
SAMPLE_STEAM = SteamData(
    most_played=[SteamGame(name="Elden Ring", app_id=1245620, hours_played=47, store_url="https://store.steampowered.com/app/1245620")],
    recently_played=[],
)
SAMPLE_TRAKT = TraktData(
    history=[TraktItem(title="Dune: Part Two", year=2024, media_type="movie", trakt_url="https://trakt.tv/movies/dune-part-two-2024", status="watched")],
    watchlist=[],
    watching=None,
)
SAMPLE_HEALTH = HealthSummary(avg_daily_steps=9000, last_workout_type="Running")

MOCK_GRAPH_JSON = {
    "nodes": [{"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}}],
    "edges": [],
}


@pytest.mark.anyio
async def test_synthesize_agentic_returns_graph_output():
    """Synthesizer should handle a single-step loop: Claude calls emit_knowledge_graph directly."""
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "emit_knowledge_graph"
    mock_tool_use.input = MOCK_GRAPH_JSON
    mock_tool_use.id = "tool_1"

    mock_message = MagicMock()
    mock_message.stop_reason = "tool_use"
    mock_message.content = [mock_tool_use]

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(return_value=mock_message)

    with patch("synthesizer.anthropic.Anthropic", return_value=mock_client):
        result = await synthesize_graph(
            github=SAMPLE_GITHUB,
            spotify=SAMPLE_SPOTIFY,
            steam=SAMPLE_STEAM,
            trakt=SAMPLE_TRAKT,
            health=SAMPLE_HEALTH,
            api_key="test-key",
        )

    assert isinstance(result, GraphOutput)
    assert any(n.id == "skill-python" for n in result.nodes)


@pytest.mark.anyio
async def test_synthesize_handles_readme_tool_call():
    """Synthesizer should call fetch_github_readme, then call emit_knowledge_graph on next turn."""
    readme_tool_use = MagicMock()
    readme_tool_use.type = "tool_use"
    readme_tool_use.name = "fetch_github_readme"
    readme_tool_use.input = {"owner": "user", "repo": "ml-project"}
    readme_tool_use.id = "tool_1"

    emit_tool_use = MagicMock()
    emit_tool_use.type = "tool_use"
    emit_tool_use.name = "emit_knowledge_graph"
    emit_tool_use.input = MOCK_GRAPH_JSON
    emit_tool_use.id = "tool_2"

    first_message = MagicMock()
    first_message.stop_reason = "tool_use"
    first_message.content = [readme_tool_use]

    second_message = MagicMock()
    second_message.stop_reason = "tool_use"
    second_message.content = [emit_tool_use]

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(side_effect=[first_message, second_message])

    with patch("synthesizer.anthropic.Anthropic", return_value=mock_client):
        with patch("synthesizer._fetch_readme", return_value="# ML Project\nA machine learning tool."):
            result = await synthesize_graph(
                github=SAMPLE_GITHUB,
                spotify=SAMPLE_SPOTIFY,
                steam=SAMPLE_STEAM,
                trakt=SAMPLE_TRAKT,
                health=SAMPLE_HEALTH,
                api_key="test-key",
            )

    assert isinstance(result, GraphOutput)
    assert mock_client.messages.create.call_count == 2
```

- [ ] **Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_synthesizer_agentic.py -v
```

Expected: FAILED — `synthesize_graph` signature mismatch

- [ ] **Step 3: Rewrite `jobs/graph-gen/synthesizer.py`**

```python
import asyncio
import json
import httpx
import anthropic
from models import GraphOutput, Node, Edge, TraktItem, HealthSummary
from sources.github import GitHubData
from sources.spotify import SpotifyData
from sources.steam import SteamData
from sources.trakt import TraktData

MAX_ITERATIONS = 10

README_TOOL = {
    "name": "fetch_github_readme",
    "description": "Fetch the README for a GitHub repository to get a richer description for a project node.",
    "input_schema": {
        "type": "object",
        "properties": {
            "owner": {"type": "string", "description": "GitHub username or org"},
            "repo":  {"type": "string", "description": "Repository name"},
        },
        "required": ["owner", "repo"],
    },
}

GRAPH_TOOL = {
    "name": "emit_knowledge_graph",
    "description": "Emit the final typed knowledge graph. Call this when you have gathered enough context.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":          {"type": "string"},
                        "type":        {"type": "string", "enum": ["skill", "project", "experience", "education", "interest", "movie", "show", "health"]},
                        "label":       {"type": "string"},
                        "description": {"type": "string"},
                        "metadata":    {"type": "object"},
                    },
                    "required": ["id", "type", "label"],
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "type":   {"type": "string", "enum": ["used_in", "worked_on", "studied_at", "interested_in", "relates_to"]},
                        "weight": {"type": "number"},
                    },
                    "required": ["source", "target", "type"],
                },
            },
        },
        "required": ["nodes", "edges"],
    },
}

SYSTEM_PROMPT = """You are a knowledge graph synthesizer for a software engineer's portfolio.

Given data from GitHub, Spotify, Steam, Trakt, and Apple Health, emit a structured knowledge graph
capturing their skills, projects, experience, education, and interests as typed nodes with weighted edges.

You may call fetch_github_readme for up to 3 repositories to get richer project descriptions.
Once you have enough context, call emit_knowledge_graph with the final graph.

Rules:
- Node IDs: stable snake_case prefixed by type (e.g. skill-python, project-ml-tool, movie-dune)
- Infer skill nodes from GitHub languages and topics
- Infer interest nodes from music genres, games, movies, and shows
- Add movie/show nodes for Trakt history with metadata.url set to the Trakt URL
- Add a health node if Apple Health data is present
- Connect skills to projects (used_in edges), interests to projects (relates_to)
- Edge weight 0.0–1.0 based on relationship strength
- Prefer fewer accurate nodes over many speculative ones
- Include metadata.url on project, movie, show, and interest nodes where a URL is available
"""


NODE_FIELDS = {"id", "type", "label", "description", "metadata"}
EDGE_FIELDS = {"source", "target", "type", "weight"}


async def _fetch_readme(owner: str, repo: str) -> str:
    """Fetch README content via GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers={"Accept": "application/vnd.github.raw"})
        if r.status_code == 200:
            return r.text[:2000]  # cap at 2000 chars
        return ""


async def synthesize_graph(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    trakt: TraktData,
    health: HealthSummary,
    api_key: str,
) -> GraphOutput:
    context = {
        "github": {
            "top_languages": github.top_languages,
            "repos": [
                {
                    "name": r.name,
                    "description": r.description,
                    "topics": r.topics,
                    "stars": r.stars,
                    "url": r.url,
                }
                for r in github.repos[:20]
            ],
        },
        "spotify": {
            "top_artists": [{"name": a.name, "url": a.url, "genres": a.genres} for a in spotify.top_artists],
            "top_genres": spotify.top_genres,
            "top_tracks": [{"name": t.name, "artist": t.artist, "url": t.url} for t in spotify.top_tracks[:5]],
        },
        "steam": {
            "most_played": [{"name": g.name, "hours": g.hours_played, "url": g.store_url} for g in steam.most_played[:5]],
            "recently_played": [g.name for g in steam.recently_played],
        },
        "trakt": {
            "history": [{"title": i.title, "type": i.media_type, "year": i.year, "url": i.trakt_url, "genres": i.genres} for i in trakt.history[:20]],
            "watchlist": [{"title": i.title, "type": i.media_type} for i in trakt.watchlist[:10]],
            "watching": {"title": trakt.watching.title, "type": trakt.watching.media_type} if trakt.watching else None,
        },
        "health": {
            "avg_daily_steps": health.avg_daily_steps,
            "avg_active_energy_kcal": health.avg_active_energy_kcal,
            "avg_sleep_hours": health.avg_sleep_hours,
            "last_workout": f"{health.last_workout_type} {health.last_workout_duration_min}min" if health.last_workout_type else None,
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": f"Here is my data:\n\n{json.dumps(context, indent=2)}"}]

    for _ in range(MAX_ITERATIONS):
        message = await asyncio.to_thread(
            client.messages.create,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[README_TOOL, GRAPH_TOOL],
            messages=messages,
        )

        tool_uses = [b for b in message.content if b.type == "tool_use"]
        if not tool_uses:
            break

        # Append assistant turn
        messages.append({"role": "assistant", "content": message.content})

        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == "emit_knowledge_graph":
                raw = tool_use.input
                nodes = [Node(**{k: v for k, v in n.items() if k in NODE_FIELDS}) for n in raw["nodes"]]
                edges = [Edge(**{**{k: v for k, v in e.items() if k in EDGE_FIELDS}, "weight": e.get("weight", 1.0)}) for e in raw["edges"]]
                return GraphOutput(nodes=nodes, edges=edges)

            elif tool_use.name == "fetch_github_readme":
                content = await _fetch_readme(tool_use.input["owner"], tool_use.input["repo"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": content or "README not available.",
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("Synthesizer exceeded max iterations without emitting graph")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_synthesizer_agentic.py -v
```

Expected: 2 passed

- [ ] **Step 5: Update old synthesizer test to match new signature**

Read `tests/test_synthesizer.py`. Update `SAMPLE_STEAM` to use `SteamGame` objects, `SAMPLE_SPOTIFY` to use `TopArtist`/`TopTrack` objects, and add `trakt` and `health` args to the `synthesize_graph` call. Also update the mock to set `mock_tool_use.name = "emit_knowledge_graph"` and `mock_message.stop_reason = "tool_use"`.

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add jobs/graph-gen/synthesizer.py jobs/graph-gen/tests/
git commit -m "feat(graph-gen): agentic synthesizer with fetch_github_readme tool"
```

---

## Task 6: Write `currently.json` + Wire Everything in `main.py`

- [ ] **Step 1: Update `jobs/graph-gen/writer.py`**

Read the file. Add `currently.json` to the uploads dict. Add a `build_currently` helper that takes the gathered data and returns the `currently.json` payload:

```python
import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from google.cloud import storage
from models import GraphOutput, ActivityFeed, NowSnapshot
from sources.spotify import SpotifyData
from sources.steam import SteamData
from sources.trakt import TraktData
from sources.github import GitHubData


def build_currently(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    trakt: TraktData,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    result: dict = {"generated_at": now}

    # working_on: top 2 recently-updated public repos
    result["working_on"] = [
        {"name": r.name, "url": r.url}
        for r in github.repos[:2]
        if r.url
    ]

    # listening_to: most recently played track
    if spotify.recently_played:
        track = spotify.recently_played[0]
        # Match to top_tracks for URL
        url = ""
        for t in spotify.top_tracks:
            if t.name == track.name:
                url = t.url
                break
        result["listening_to"] = {"artist": track.artist, "track": track.name, "url": url}
    elif spotify.top_tracks:
        t = spotify.top_tracks[0]
        result["listening_to"] = {"artist": t.artist, "track": t.name, "url": t.url}

    # playing: most recently played Steam game
    if steam.recently_played:
        g = steam.recently_played[0]
        result["playing"] = {"name": g.name, "hours": g.hours_played, "url": g.store_url}
    elif steam.most_played:
        g = steam.most_played[0]
        result["playing"] = {"name": g.name, "hours": g.hours_played, "url": g.store_url}

    # watching: currently watching show, else most recent history item
    if trakt.watching:
        w = trakt.watching
        entry: dict = {"title": w.title, "url": w.trakt_url}
        if w.media_type == "show":
            entry["season"] = None  # season unknown from /watching endpoint
        result["watching"] = entry
    elif trakt.history:
        item = trakt.history[0]
        entry = {"title": item.title, "url": item.trakt_url}
        result["watching"] = entry

    return result


def _serialise(obj) -> str:
    return json.dumps(asdict(obj), indent=2, default=str)


def _sync_upload(bucket_name: str, uploads: dict[str, str]) -> None:
    client = storage.Client()
    gcs_bucket = client.bucket(bucket_name)
    for key, content in uploads.items():
        blob = gcs_bucket.blob(key)
        blob.cache_control = "public, max-age=300"
        blob.upload_from_string(content, content_type="application/json")


async def write_outputs(
    bucket: str,
    graph: GraphOutput,
    feed: ActivityFeed,
    now: NowSnapshot,
    currently: dict,
) -> None:
    uploads = {
        "graph.json": _serialise(graph),
        "activity-feed.json": _serialise(feed),
        "now.json": _serialise(now),
        "currently.json": json.dumps(currently, indent=2),
    }
    await asyncio.to_thread(_sync_upload, bucket, uploads)
```

- [ ] **Step 2: Run existing writer test — fix if needed**

```bash
uv run pytest tests/test_writer.py -v
```

The `write_outputs` signature changed (added `currently` param). Update the test to pass `currently={}`.

- [ ] **Step 3: Update `jobs/graph-gen/main.py`**

```python
import asyncio
import os
from datetime import datetime, timezone

from models import ActivityFeed, ActivityItem, NowSnapshot
from sources.github import fetch_github
from sources.spotify import fetch_spotify
from sources.steam import fetch_steam
from sources.trakt import fetch_trakt
from sources.apple_health import fetch_apple_health
from synthesizer import synthesize_graph
from writer import write_outputs, build_currently


def _build_activity_feed(github, spotify, steam):
    items = []

    for track in spotify.recently_played[:5]:
        items.append(ActivityItem(
            type="track",
            title=track.name,
            subtitle=track.artist,
            timestamp=track.played_at,
        ))

    for game in steam.recently_played[:3]:
        items.append(ActivityItem(
            type="game",
            title=game.name,
            subtitle="Steam",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    items.sort(key=lambda i: i.timestamp, reverse=True)
    return ActivityFeed(items=items[:10])


def _build_now(github, spotify, steam):
    return NowSnapshot(
        current_projects=[r.name for r in github.repos[:3]],
        listening_to=[a.name for a in spotify.top_artists[:3]],
        recently_played_games=[g.name for g in steam.recently_played[:3]],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


async def run():
    bucket = os.environ["GCS_BUCKET"]
    api_key = os.environ["ANTHROPIC_API_KEY"]
    health_prefix = os.environ.get("APPLE_HEALTH_PREFIX", "data/ephemeral/apple-health/")

    print("Fetching sources in parallel...")
    github, spotify, steam, trakt, health = await asyncio.gather(
        fetch_github(username=os.environ["GITHUB_USERNAME"], token=os.environ["GITHUB_TOKEN"]),
        fetch_spotify(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            refresh_token=os.environ["SPOTIFY_REFRESH_TOKEN"],
        ),
        fetch_steam(api_key=os.environ["STEAM_API_KEY"], user_id=os.environ["STEAM_USER_ID"]),
        fetch_trakt(
            client_id=os.environ["TRAKT_CLIENT_ID"],
            client_secret=os.environ["TRAKT_CLIENT_SECRET"],
            refresh_token=os.environ["TRAKT_REFRESH_TOKEN"],
        ),
        fetch_apple_health(bucket_name=bucket, prefix=health_prefix),
    )
    print(f"Fetched: {len(github.repos)} repos, {len(spotify.top_artists)} artists, "
          f"{len(steam.most_played)} games, {len(trakt.history)} trakt items, "
          f"steps={health.avg_daily_steps}")

    print("Synthesising knowledge graph with Claude...")
    graph = await synthesize_graph(
        github=github, spotify=spotify, steam=steam,
        trakt=trakt, health=health, api_key=api_key,
    )
    print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    feed = _build_activity_feed(github, spotify, steam)
    now = _build_now(github, spotify, steam)
    currently = build_currently(github, spotify, steam, trakt)

    print("Writing outputs to GCS...")
    await write_outputs(bucket=bucket, graph=graph, feed=feed, now=now, currently=currently)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 4: Run full test suite**

```bash
cd jobs/graph-gen
uv run pytest -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add jobs/graph-gen/
git commit -m "feat(graph-gen): currently.json writer, wire trakt + health into main"
```

---

## Task 7: Push, Deploy, and Run

- [ ] **Step 1: Push all commits**

```bash
git push
```

- [ ] **Step 2: Trigger deploy-job workflow**

GitHub → Actions → "Deploy Graph-Gen Job" → Run workflow. Expected: green within ~5 minutes.

- [ ] **Step 3: Run the job**

```bash
gcloud run jobs execute graph-gen --region us-east1 --project adits-gcp --wait
```

Expected: exits 0, logs show "Done."

- [ ] **Step 4: Verify outputs in GCS**

```bash
gsutil stat gs://adits-gcp-static-site/graph.json
gsutil stat gs://adits-gcp-static-site/currently.json
```

Expected: both files exist with recent timestamps.

- [ ] **Step 5: Verify currently.json content**

```bash
gsutil cat gs://adits-gcp-static-site/currently.json
```

Expected: JSON with `generated_at`, `working_on`, and at least one of `listening_to`, `playing`, `watching`.

- [ ] **Step 6: Verify graph loads on site**

Visit `https://aditya.tapshalkar.com` — graph should render with enriched nodes.
