# Graph-Gen Job Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the scheduled Cloud Run Job that fetches data from GitHub, Spotify, and Steam APIs in parallel, synthesises a typed knowledge graph via Claude, and writes `graph.json`, `activity-feed.json`, and `now.json` to GCS.

**Architecture:** A single `main.py` orchestrator runs `asyncio.gather` over three source modules, feeds normalised data to a Claude API synthesiser (structured output via tool use), then writes outputs to GCS and invalidates the CDN cache. All external calls are isolated behind thin async functions making them straightforward to mock in tests.

**Tech Stack:** Python 3.13, uv, anthropic SDK, httpx (for GitHub/Spotify/Steam), google-cloud-storage, pytest, pytest-asyncio

**Prerequisites:** infra plan complete (Secret Manager secrets populated, GCS bucket exists)

---

## File Map

```
jobs/graph-gen/
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── .env.example
├── main.py                    # orchestrator — entry point
├── synthesizer.py             # Claude API call → GraphOutput
├── writer.py                  # writes JSON files to GCS + CDN invalidation
├── models.py                  # shared dataclasses: Node, Edge, GraphOutput, ActivityFeed, Now
├── sources/
│   ├── __init__.py
│   ├── github.py              # fetch repos, languages, contribution stats, pinned READMEs
│   ├── spotify.py             # fetch top artists/tracks/genres, recently played
│   └── steam.py               # fetch game library, recent playtime
└── tests/
    ├── conftest.py             # shared fixtures with mocked API responses
    ├── test_github.py
    ├── test_spotify.py
    ├── test_steam.py
    ├── test_synthesizer.py
    └── test_writer.py
```

---

## Task 1: Project Scaffold + Models

- [ ] **Step 1: Create `jobs/graph-gen/pyproject.toml`**

```toml
[project]
name = "graph-gen"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "anthropic>=0.40",
    "httpx>=0.28",
    "google-cloud-storage>=2.18",
    "google-cloud-compute>=1.19",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "anyio>=4.7",
    "respx>=0.21",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Install dependencies**

```bash
cd jobs/graph-gen
uv sync
```

- [ ] **Step 3: Create `jobs/graph-gen/.env.example`**

```
GCS_BUCKET=your-project-static-site
GCP_PROJECT_ID=your-gcp-project
CDN_URL_MAP_NAME=tapshalkar-url-map
ANTHROPIC_API_KEY=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REFRESH_TOKEN=
STEAM_API_KEY=
STEAM_USER_ID=76561198xxxxxxxxx
GITHUB_TOKEN=
GITHUB_USERNAME=adityataps
```

- [ ] **Step 4: Create `jobs/graph-gen/models.py`**

```python
from dataclasses import dataclass, field


@dataclass
class Node:
    id: str           # snake_case, e.g. "skill-python"
    type: str         # skill | project | experience | education | interest
    label: str
    description: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    source: str       # node id
    target: str       # node id
    type: str         # used_in | worked_on | studied_at | interested_in | relates_to
    weight: float = 1.0


@dataclass
class GraphOutput:
    nodes: list[Node]
    edges: list[Edge]


@dataclass
class ActivityItem:
    type: str         # "commit" | "track" | "game"
    title: str
    subtitle: str
    timestamp: str    # ISO 8601
    url: str = ""


@dataclass
class ActivityFeed:
    items: list[ActivityItem]


@dataclass
class NowSnapshot:
    current_projects: list[str]
    listening_to: list[str]      # top 3 Spotify artists
    recently_played_games: list[str]
    updated_at: str              # ISO 8601
```

- [ ] **Step 5: Commit scaffold**

```bash
git add jobs/graph-gen/
git commit -m "feat(graph-gen): project scaffold and models"
```

---

## Task 2: GitHub Source

- [ ] **Step 1: Create failing test `jobs/graph-gen/tests/test_github.py`**

```python
import pytest
import respx
import httpx
from sources.github import fetch_github, GitHubData


REPOS_RESPONSE = [
    {
        "name": "cool-project",
        "description": "A cool ML project",
        "language": "Python",
        "stargazers_count": 12,
        "html_url": "https://github.com/adityataps/cool-project",
        "topics": ["machine-learning", "python"],
    }
]

LANGUAGES_RESPONSE = {"Python": 8000, "TypeScript": 2000}


@pytest.mark.anyio
async def test_fetch_github_returns_repos():
    with respx.mock:
        respx.get("https://api.github.com/users/adityataps/repos").mock(
            return_value=httpx.Response(200, json=REPOS_RESPONSE)
        )
        respx.get("https://api.github.com/repos/adityataps/cool-project/languages").mock(
            return_value=httpx.Response(200, json=LANGUAGES_RESPONSE)
        )

        data = await fetch_github(username="adityataps", token="test-token")

    assert isinstance(data, GitHubData)
    assert len(data.repos) == 1
    assert data.repos[0].name == "cool-project"
    assert "Python" in data.repos[0].languages
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd jobs/graph-gen
uv run pytest tests/test_github.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'sources.github'`

- [ ] **Step 3: Create `jobs/graph-gen/sources/__init__.py`** (empty)

- [ ] **Step 4: Create `jobs/graph-gen/sources/github.py`**

```python
import asyncio
from dataclasses import dataclass, field
import httpx


@dataclass
class RepoData:
    name: str
    description: str
    languages: dict[str, int]
    stars: int
    url: str
    topics: list[str]


@dataclass
class GitHubData:
    repos: list[RepoData]
    top_languages: list[str]     # sorted by total bytes across all repos


async def _fetch_repo_languages(client: httpx.AsyncClient, username: str, repo_name: str) -> dict[str, int]:
    r = await client.get(f"https://api.github.com/repos/{username}/{repo_name}/languages")
    r.raise_for_status()
    return r.json()


async def fetch_github(username: str, token: str) -> GitHubData:
    headers = {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        r = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 30, "type": "public"},
        )
        r.raise_for_status()
        raw_repos = r.json()

        language_tasks = [
            _fetch_repo_languages(client, username, repo["name"])
            for repo in raw_repos
        ]
        all_languages = await asyncio.gather(*language_tasks)

    repos = [
        RepoData(
            name=raw["name"],
            description=raw.get("description") or "",
            languages=langs,
            stars=raw.get("stargazers_count", 0),
            url=raw.get("html_url", ""),
            topics=raw.get("topics", []),
        )
        for raw, langs in zip(raw_repos, all_languages)
    ]

    # Aggregate language bytes across all repos
    lang_totals: dict[str, int] = {}
    for repo in repos:
        for lang, bytes_count in repo.languages.items():
            lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count

    top_languages = sorted(lang_totals, key=lambda l: lang_totals[l], reverse=True)[:10]

    return GitHubData(repos=repos, top_languages=top_languages)
```

- [ ] **Step 5: Run test — verify it passes**

```bash
uv run pytest tests/test_github.py -v
```

Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add jobs/graph-gen/sources/ jobs/graph-gen/tests/test_github.py
git commit -m "feat(graph-gen): github source"
```

---

## Task 3: Spotify Source

- [ ] **Step 1: Create failing test `jobs/graph-gen/tests/test_spotify.py`**

```python
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
```

- [ ] **Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_spotify.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'sources.spotify'`

- [ ] **Step 3: Create `jobs/graph-gen/sources/spotify.py`**

```python
import base64
from dataclasses import dataclass
import httpx


@dataclass
class RecentTrack:
    name: str
    artist: str
    played_at: str


@dataclass
class SpotifyData:
    top_artists: list[str]
    top_tracks: list[str]
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

    top_artists = [a["name"] for a in artists_r.json()["items"]]
    top_tracks = [t["name"] for t in tracks_r.json()["items"]]

    genre_counts: dict[str, int] = {}
    for artist in artists_r.json()["items"]:
        for genre in artist.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    top_genres = sorted(genre_counts, key=lambda g: genre_counts[g], reverse=True)[:10]

    recently_played = [
        RecentTrack(
            name=item["track"]["name"],
            artist=item["track"]["artists"][0]["name"],
            played_at=item["played_at"],
        )
        for item in recent_r.json()["items"]
    ]

    return SpotifyData(
        top_artists=top_artists,
        top_tracks=top_tracks,
        top_genres=top_genres,
        recently_played=recently_played,
    )
```

- [ ] **Step 4: Add missing `asyncio` import to `spotify.py`**

Add `import asyncio` at the top of `sources/spotify.py`.

- [ ] **Step 5: Run test — verify it passes**

```bash
uv run pytest tests/test_spotify.py -v
```

Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add jobs/graph-gen/sources/spotify.py jobs/graph-gen/tests/test_spotify.py
git commit -m "feat(graph-gen): spotify source"
```

---

## Task 4: Steam Source

- [ ] **Step 1: Create failing test `jobs/graph-gen/tests/test_steam.py`**

```python
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
```

- [ ] **Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_steam.py -v
```

Expected: `FAILED`

- [ ] **Step 3: Create `jobs/graph-gen/sources/steam.py`**

```python
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

    owned_games = owned_r.json()["response"].get("games", [])
    recent_games = recent_r.json()["response"].get("games", [])

    most_played = [
        g["name"]
        for g in sorted(owned_games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:10]
    ]
    recently_played = [g["name"] for g in recent_games]

    return SteamData(most_played=most_played, recently_played=recently_played)
```

- [ ] **Step 4: Add `import asyncio` to `steam.py`**

- [ ] **Step 5: Run test — verify it passes**

```bash
uv run pytest tests/test_steam.py -v
```

Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add jobs/graph-gen/sources/steam.py jobs/graph-gen/tests/test_steam.py
git commit -m "feat(graph-gen): steam source"
```

---

## Task 5: Claude Synthesizer

- [ ] **Step 1: Create failing test `jobs/graph-gen/tests/test_synthesizer.py`**

```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from synthesizer import synthesize_graph
from models import GraphOutput
from sources.github import GitHubData, RepoData
from sources.spotify import SpotifyData, RecentTrack
from sources.steam import SteamData


SAMPLE_GITHUB = GitHubData(
    repos=[RepoData(name="ml-project", description="ML stuff", languages={"Python": 5000}, stars=3, url="", topics=["ml"])],
    top_languages=["Python"],
)
SAMPLE_SPOTIFY = SpotifyData(top_artists=["Kendrick Lamar"], top_tracks=["HUMBLE."], top_genres=["hip hop"], recently_played=[])
SAMPLE_STEAM = SteamData(most_played=["Counter-Strike 2"], recently_played=["Counter-Strike 2"])

MOCK_GRAPH_JSON = json.dumps({
    "nodes": [
        {"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}},
        {"id": "interest-hip-hop", "type": "interest", "label": "Hip Hop", "description": "", "metadata": {}},
    ],
    "edges": [
        {"source": "skill-python", "target": "skill-python", "type": "relates_to", "weight": 1.0}
    ]
})


@pytest.mark.anyio
async def test_synthesize_returns_graph_output():
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(MOCK_GRAPH_JSON)

    mock_message = MagicMock()
    mock_message.content = [mock_tool_use]

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(return_value=mock_message)

    with patch("synthesizer.anthropic.Anthropic", return_value=mock_client):
        result = await synthesize_graph(
            github=SAMPLE_GITHUB,
            spotify=SAMPLE_SPOTIFY,
            steam=SAMPLE_STEAM,
            api_key="test-key",
        )

    assert isinstance(result, GraphOutput)
    assert any(n.id == "skill-python" for n in result.nodes)
    assert len(result.edges) == 1
```

- [ ] **Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_synthesizer.py -v
```

Expected: `FAILED`

- [ ] **Step 3: Create `jobs/graph-gen/synthesizer.py`**

```python
import json
import anthropic
from models import GraphOutput, Node, Edge
from sources.github import GitHubData
from sources.spotify import SpotifyData
from sources.steam import SteamData

GRAPH_TOOL = {
    "name": "emit_knowledge_graph",
    "description": "Emit a typed knowledge graph representing a person's skills, projects, experience, education, and interests.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":          {"type": "string", "description": "Stable snake_case identifier, e.g. skill-python"},
                        "type":        {"type": "string", "enum": ["skill", "project", "experience", "education", "interest"]},
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

SYSTEM_PROMPT = """You are a knowledge graph synthesizer. Given data about a software engineer
pulled from GitHub, Spotify, and Steam, emit a structured knowledge graph that captures their
skills, projects, experience, education, and interests as typed nodes with weighted edges.

Rules:
- Node IDs must be stable snake_case strings prefixed by type (e.g. skill-python, project-ml-tool)
- Infer skills from GitHub languages and repo topics
- Infer interest nodes from music genres and games
- Connect skills to projects they are used in (used_in edges)
- Set edge weight 0.0–1.0 based on strength of relationship
- Omit nodes you cannot confidently infer — prefer fewer, accurate nodes over many speculative ones
"""


async def synthesize_graph(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    api_key: str,
) -> GraphOutput:
    context = {
        "github": {
            "top_languages": github.top_languages,
            "repos": [
                {"name": r.name, "description": r.description, "topics": r.topics, "stars": r.stars}
                for r in github.repos[:20]
            ],
        },
        "spotify": {
            "top_artists": spotify.top_artists,
            "top_genres": spotify.top_genres,
            "top_tracks": spotify.top_tracks[:5],
        },
        "steam": {
            "most_played": steam.most_played[:5],
            "recently_played": steam.recently_played,
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[GRAPH_TOOL],
        tool_choice={"type": "tool", "name": "emit_knowledge_graph"},
        messages=[{"role": "user", "content": f"Here is my data:\n\n{json.dumps(context, indent=2)}"}],
    )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    raw = tool_use.input

    nodes = [Node(**n) for n in raw["nodes"]]
    edges = [Edge(**{**e, "weight": e.get("weight", 1.0)}) for e in raw["edges"]]

    return GraphOutput(nodes=nodes, edges=edges)
```

- [ ] **Step 4: Run test — verify it passes**

```bash
uv run pytest tests/test_synthesizer.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add jobs/graph-gen/synthesizer.py jobs/graph-gen/tests/test_synthesizer.py
git commit -m "feat(graph-gen): claude synthesizer"
```

---

## Task 6: GCS Writer + Orchestrator

- [ ] **Step 1: Create failing test `jobs/graph-gen/tests/test_writer.py`**

```python
import json
import pytest
from dataclasses import asdict
from unittest.mock import AsyncMock, patch, MagicMock
from writer import write_outputs
from models import GraphOutput, Node, Edge, ActivityFeed, ActivityItem, NowSnapshot


GRAPH = GraphOutput(
    nodes=[Node(id="skill-python", type="skill", label="Python")],
    edges=[],
)
FEED = ActivityFeed(items=[ActivityItem(type="commit", title="feat: add thing", subtitle="tapshalkar.com", timestamp="2026-04-09T00:00:00Z")])
NOW = NowSnapshot(current_projects=["tapshalkar.com"], listening_to=["Kendrick Lamar"], recently_played_games=["CS2"], updated_at="2026-04-09T00:00:00Z")


@pytest.mark.anyio
async def test_write_outputs_uploads_three_files():
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    with patch("writer.storage.Client", return_value=mock_client):
        await write_outputs(bucket="test-bucket", graph=GRAPH, feed=FEED, now=NOW)

    assert mock_bucket.blob.call_count == 3
    uploaded_keys = {call.args[0] for call in mock_bucket.blob.call_args_list}
    assert uploaded_keys == {"graph.json", "activity-feed.json", "now.json"}
```

- [ ] **Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_writer.py -v
```

Expected: `FAILED`

- [ ] **Step 3: Create `jobs/graph-gen/writer.py`**

```python
import json
from dataclasses import asdict
from google.cloud import storage
from models import GraphOutput, ActivityFeed, NowSnapshot


def _serialise(obj) -> str:
    return json.dumps(asdict(obj), indent=2, default=str)


async def write_outputs(
    bucket: str,
    graph: GraphOutput,
    feed: ActivityFeed,
    now: NowSnapshot,
) -> None:
    client = storage.Client()
    gcs_bucket = client.bucket(bucket)

    uploads = {
        "graph.json": _serialise(graph),
        "activity-feed.json": _serialise(feed),
        "now.json": _serialise(now),
    }

    for key, content in uploads.items():
        blob = gcs_bucket.blob(key)
        blob.upload_from_string(content, content_type="application/json")
        blob.cache_control = "public, max-age=300"
        blob.patch()
```

- [ ] **Step 4: Run test — verify it passes**

```bash
uv run pytest tests/test_writer.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Create `jobs/graph-gen/main.py`**

```python
import asyncio
import os
from datetime import datetime, timezone

from models import ActivityFeed, ActivityItem, NowSnapshot
from sources.github import fetch_github
from sources.spotify import fetch_spotify
from sources.steam import fetch_steam
from synthesizer import synthesize_graph
from writer import write_outputs


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
            title=game,
            subtitle="Steam",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    items.sort(key=lambda i: i.timestamp, reverse=True)
    return ActivityFeed(items=items[:10])


def _build_now(github, spotify, steam):
    return NowSnapshot(
        current_projects=[r.name for r in github.repos[:3]],
        listening_to=spotify.top_artists[:3],
        recently_played_games=steam.recently_played[:3],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


async def run():
    bucket = os.environ["GCS_BUCKET"]
    api_key = os.environ["ANTHROPIC_API_KEY"]

    print("Fetching sources in parallel...")
    github, spotify, steam = await asyncio.gather(
        fetch_github(username=os.environ["GITHUB_USERNAME"], token=os.environ["GITHUB_TOKEN"]),
        fetch_spotify(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            refresh_token=os.environ["SPOTIFY_REFRESH_TOKEN"],
        ),
        fetch_steam(api_key=os.environ["STEAM_API_KEY"], user_id=os.environ["STEAM_USER_ID"]),
    )
    print(f"Fetched: {len(github.repos)} repos, {len(spotify.top_artists)} artists, {len(steam.most_played)} games")

    print("Synthesising knowledge graph with Claude...")
    graph = await synthesize_graph(github=github, spotify=spotify, steam=steam, api_key=api_key)
    print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    feed = _build_activity_feed(github, spotify, steam)
    now = _build_now(github, spotify, steam)

    print("Writing outputs to GCS...")
    await write_outputs(bucket=bucket, graph=graph, feed=feed, now=now)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add jobs/graph-gen/
git commit -m "feat(graph-gen): writer, orchestrator, and full pipeline"
```

---

## Task 7: Dockerfile + Local Test Run

- [ ] **Step 1: Create `jobs/graph-gen/Dockerfile`**

```dockerfile
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "python", "main.py"]
```

- [ ] **Step 2: Build image**

```bash
cd jobs/graph-gen
docker build -t graph-gen:local .
```

Expected: `Successfully built ...`

- [ ] **Step 3: Run a dry test with real env vars** (optional — requires secrets to be available)

```bash
docker run --rm \
  -e GCS_BUCKET=your-project-static-site \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e GITHUB_TOKEN=ghp_... \
  -e GITHUB_USERNAME=adityataps \
  -e SPOTIFY_CLIENT_ID=... \
  -e SPOTIFY_CLIENT_SECRET=... \
  -e SPOTIFY_REFRESH_TOKEN=... \
  -e STEAM_API_KEY=... \
  -e STEAM_USER_ID=... \
  graph-gen:local
```

Expected output:
```
Fetching sources in parallel...
Fetched: 30 repos, 10 artists, 10 games
Synthesising knowledge graph with Claude...
Graph: ~25 nodes, ~30 edges
Writing outputs to GCS...
Done.
```

- [ ] **Step 4: Verify GCS outputs**

```bash
gsutil cat gs://your-project-static-site/graph.json | python3 -m json.tool | head -30
```

Expected: Valid JSON with `nodes` and `edges` arrays.

- [ ] **Step 5: Commit**

```bash
git add jobs/graph-gen/Dockerfile
git commit -m "feat(graph-gen): dockerfile"
```
