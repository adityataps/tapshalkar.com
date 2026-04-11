# Spotify Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the knowledge graph with granular Spotify content (artists, albums, podcasts, audiobooks, genres) using a `type: "interest"` + `metadata.subtype` model, and trigger a Cloud Run Job execution after every successful image deploy.

**Architecture:** Three new Spotify API fetches (saved shows, audiobooks, expanded recently-played) are added to `sources/spotify.py`. Enriched data flows into the existing agentic synthesizer via an updated context dict and system prompt. The synthesizer emits `interest` nodes with subtypes; `movie`/`show` fold into the same type. The frontend reads `metadata.subtype` for tooltip and sidebar labels. A new CI step executes the Cloud Run Job immediately after each successful image deploy.

**Tech Stack:** Python 3.13, httpx, respx (test mocking), Spotify Web API, Claude API, Next.js/TypeScript, GitHub Actions, gcloud CLI

---

## File Map

| File | Action | What changes |
|---|---|---|
| `jobs/graph-gen/sources/spotify.py` | Modify | 3 new dataclasses, 2 new API fetches, expand recently-played to 50, album deduplication, short_term time range |
| `jobs/graph-gen/tests/test_spotify.py` | Modify | Add mocks for the 2 new endpoints so existing test doesn't error on unmatched routes |
| `jobs/graph-gen/tests/test_spotify_enriched.py` | Create | 3 focused tests for saved_shows, saved_audiobooks, recent_albums |
| `jobs/graph-gen/synthesizer.py` | Modify | GRAPH_TOOL enum drops movie/show, SYSTEM_PROMPT gains subtype rules, context dict gains 3 new Spotify fields |
| `jobs/graph-gen/tests/test_synthesizer.py` | Modify | Update SAMPLE_SPOTIFY fixture with new fields |
| `frontend/components/graph/ForceGraph.tsx` | Modify | Remove movie/show from type union and NODE_COLORS, subtype-aware nodeLabel |
| `frontend/components/graph/GraphSidebar.tsx` | Modify | Show metadata.subtype instead of node.type in the red label |
| `.github/workflows/deploy-job.yml` | Modify | Add `gcloud run jobs execute --wait` step after image update |

---

## Task 1: Extend spotify.py — new dataclasses, fetches, album extraction

**Files:**
- Modify: `jobs/graph-gen/sources/spotify.py`
- Create: `jobs/graph-gen/tests/test_spotify_enriched.py`
- Modify: `jobs/graph-gen/tests/test_spotify.py`

- [ ] **Step 1: Write failing tests for new Spotify fields**

Create `jobs/graph-gen/tests/test_spotify_enriched.py`:

```python
import pytest
import respx
import httpx
from sources.spotify import fetch_spotify, SpotifyData

TOKEN_RESPONSE = {"access_token": "test-access-token", "token_type": "Bearer"}
TOP_ARTISTS_RESPONSE = {"items": [{"name": "Kendrick Lamar", "genres": ["hip hop"], "id": "ka1", "external_urls": {"spotify": "https://open.spotify.com/artist/ka1"}}]}
TOP_TRACKS_RESPONSE = {"items": [{"name": "HUMBLE.", "artists": [{"name": "Kendrick Lamar"}], "external_urls": {"spotify": "https://open.spotify.com/track/hb1"}}]}
RECENTLY_PLAYED_RESPONSE = {
    "items": [
        {
            "track": {
                "name": "HUMBLE.",
                "artists": [{"name": "Kendrick Lamar"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/hb1"},
                "album": {"id": "alb1", "name": "DAMN.", "external_urls": {"spotify": "https://open.spotify.com/album/alb1"}},
            },
            "played_at": "2026-04-09T10:00:00Z",
        },
        {
            "track": {
                "name": "Creep",
                "artists": [{"name": "Radiohead"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/creep1"},
                "album": {"id": "alb2", "name": "Pablo Honey", "external_urls": {"spotify": "https://open.spotify.com/album/alb2"}},
            },
            "played_at": "2026-04-09T09:00:00Z",
        },
        {
            "track": {
                "name": "DNA.",
                "artists": [{"name": "Kendrick Lamar"}],
                "external_urls": {"spotify": "https://open.spotify.com/track/dna1"},
                "album": {"id": "alb1", "name": "DAMN.", "external_urls": {"spotify": "https://open.spotify.com/album/alb1"}},
            },
            "played_at": "2026-04-09T08:00:00Z",
        },
    ]
}
SHOWS_RESPONSE = {
    "items": [
        {
            "show": {
                "name": "Lex Fridman Podcast",
                "publisher": "Lex Fridman",
                "external_urls": {"spotify": "https://open.spotify.com/show/lex1"},
                "description": "Conversations about science and technology.",
            }
        }
    ]
}
AUDIOBOOKS_RESPONSE = {
    "items": [
        {
            "name": "Atomic Habits",
            "authors": [{"name": "James Clear"}],
            "external_urls": {"spotify": "https://open.spotify.com/audiobook/ab1"},
        }
    ]
}


def _mock_all(recently_played=None, shows=None, audiobooks=None):
    """Helper: registers all 5 endpoint mocks."""
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
        return_value=httpx.Response(200, json=recently_played or RECENTLY_PLAYED_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/shows").mock(
        return_value=httpx.Response(200, json=shows or SHOWS_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me/audiobooks").mock(
        return_value=httpx.Response(200, json=audiobooks or AUDIOBOOKS_RESPONSE)
    )


@pytest.mark.anyio
async def test_fetch_spotify_includes_saved_shows():
    with respx.mock:
        _mock_all()
        data = await fetch_spotify(client_id="id", client_secret="secret", refresh_token="token")

    assert len(data.saved_shows) == 1
    assert data.saved_shows[0].name == "Lex Fridman Podcast"
    assert data.saved_shows[0].publisher == "Lex Fridman"
    assert data.saved_shows[0].url == "https://open.spotify.com/show/lex1"
    assert "science" in data.saved_shows[0].description


@pytest.mark.anyio
async def test_fetch_spotify_includes_audiobooks():
    with respx.mock:
        _mock_all()
        data = await fetch_spotify(client_id="id", client_secret="secret", refresh_token="token")

    assert len(data.saved_audiobooks) == 1
    assert data.saved_audiobooks[0].name == "Atomic Habits"
    assert data.saved_audiobooks[0].author == "James Clear"
    assert data.saved_audiobooks[0].url == "https://open.spotify.com/audiobook/ab1"


@pytest.mark.anyio
async def test_fetch_spotify_extracts_recent_albums_deduped():
    with respx.mock:
        _mock_all()
        data = await fetch_spotify(client_id="id", client_secret="secret", refresh_token="token")

    # 3 tracks across 2 albums — DAMN. appears twice but should be deduped
    assert len(data.recent_albums) == 2
    names = [a.name for a in data.recent_albums]
    assert "DAMN." in names
    assert "Pablo Honey" in names
    assert data.recent_albums[0].url == "https://open.spotify.com/album/alb1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd jobs/graph-gen && uv run pytest tests/test_spotify_enriched.py -v
```

Expected: FAIL — `SpotifyData` has no `saved_shows` attribute.

- [ ] **Step 3: Update `test_spotify.py` to add mocks for the 2 new endpoints**

Add these two mocks inside the `with respx.mock:` block in `test_fetch_spotify_returns_data` (after the existing 3 mocks). This prevents the test from erroring on unmatched routes after we add the new fetches:

```python
respx.get("https://api.spotify.com/v1/me/shows").mock(
    return_value=httpx.Response(200, json={"items": []})
)
respx.get("https://api.spotify.com/v1/me/audiobooks").mock(
    return_value=httpx.Response(200, json={"items": []})
)
```

Also add these assertions (the existing test must still pass all its original assertions):

```python
assert data.saved_shows == []
assert data.saved_audiobooks == []
assert data.recent_albums == []
```

- [ ] **Step 4: Implement new dataclasses and `SpotifyData` fields in `spotify.py`**

Add after the `TopTrack` dataclass:

```python
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
```

Update `SpotifyData` (add three new fields with defaults so existing fixtures don't break):

```python
from dataclasses import dataclass, field

@dataclass
class SpotifyData:
    top_artists: list[TopArtist]
    top_tracks: list[TopTrack]
    top_genres: list[str]
    recently_played: list[RecentTrack]
    saved_shows: list[SavedShow] = field(default_factory=list)
    saved_audiobooks: list[SavedAudiobook] = field(default_factory=list)
    recent_albums: list[RecentAlbum] = field(default_factory=list)
```

- [ ] **Step 5: Update `fetch_spotify` to call the 2 new endpoints and parse results**

Replace the `asyncio.gather` call and everything after it with:

```python
async def fetch_spotify(client_id: str, client_secret: str, refresh_token: str) -> SpotifyData:
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_access_token(client, client_id, client_secret, refresh_token)
        headers = {"Authorization": f"Bearer {token}"}

        artists_r, tracks_r, recent_r, shows_r, audiobooks_r = await asyncio.gather(
            client.get("https://api.spotify.com/v1/me/top/artists", headers=headers, params={"limit": 10, "time_range": "short_term"}),
            client.get("https://api.spotify.com/v1/me/top/tracks", headers=headers, params={"limit": 10, "time_range": "short_term"}),
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

    recently_played = [
        RecentTrack(
            name=item["track"]["name"],
            artist=item["track"]["artists"][0]["name"],
            played_at=item["played_at"],
            url=item["track"].get("external_urls", {}).get("spotify", ""),
        )
        for item in recent_r.json()["items"]
    ]

    seen_album_ids: set[str] = set()
    recent_albums: list[RecentAlbum] = []
    for item in recent_r.json()["items"]:
        album = item["track"].get("album", {})
        album_id = album.get("id")
        if album_id and album_id not in seen_album_ids:
            seen_album_ids.add(album_id)
            recent_albums.append(RecentAlbum(
                name=album.get("name", ""),
                artist=item["track"]["artists"][0]["name"],
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
```

- [ ] **Step 6: Run all Spotify tests to verify they pass**

```bash
cd jobs/graph-gen && uv run pytest tests/test_spotify.py tests/test_spotify_enriched.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add jobs/graph-gen/sources/spotify.py \
        jobs/graph-gen/tests/test_spotify.py \
        jobs/graph-gen/tests/test_spotify_enriched.py
git commit -m "feat(spotify): add saved shows, audiobooks, and recent albums to SpotifyData"
```

---

## Task 2: Update synthesizer — fold movie/show into interest, add subtype guidance

**Files:**
- Modify: `jobs/graph-gen/synthesizer.py`
- Modify: `jobs/graph-gen/tests/test_synthesizer.py`

- [ ] **Step 1: Update `SAMPLE_SPOTIFY` fixture in `test_synthesizer.py`**

The fixture currently constructs `SpotifyData` without the new fields. Since they have defaults, this will already work — but add the `MOCK_GRAPH_JSON` interest node to use `metadata.subtype` to match what the updated synthesizer will emit:

Replace the `MOCK_GRAPH_JSON` in `tests/test_synthesizer.py`:

```python
MOCK_GRAPH_JSON = {
    "nodes": [
        {"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}},
        {"id": "interest-genre-hip-hop", "type": "interest", "label": "Hip Hop", "description": "", "metadata": {"subtype": "genre"}},
    ],
    "edges": [
        {"source": "skill-python", "target": "interest-genre-hip-hop", "type": "relates_to", "weight": 0.5}
    ]
}
```

- [ ] **Step 2: Run existing synthesizer test to confirm it still passes before touching synthesizer.py**

```bash
cd jobs/graph-gen && uv run pytest tests/test_synthesizer.py tests/test_synthesizer_agentic.py -v
```

Expected: PASS (defaults mean SpotifyData still constructs fine).

- [ ] **Step 3: Update `GRAPH_TOOL` in `synthesizer.py` — remove movie/show from enum**

Replace the `"type"` field enum in `GRAPH_TOOL["input_schema"]["properties"]["nodes"]["items"]["properties"]["type"]`:

```python
"type": {"type": "string", "enum": ["skill", "project", "experience", "education", "interest", "health"]},
```

Also add `"subtype"` as a documented property inside `"metadata"` in the `GRAPH_TOOL` schema to guide Claude:

```python
"metadata": {
    "type": "object",
    "description": "For interest nodes set subtype to one of: artist, album, track, podcast, audiobook, movie, show, genre",
},
```

- [ ] **Step 4: Update `SYSTEM_PROMPT` in `synthesizer.py`**

Replace the existing `SYSTEM_PROMPT` string with:

```python
SYSTEM_PROMPT = """You are a knowledge graph synthesizer for a software engineer's portfolio.

Given data from GitHub, Spotify, Steam, Trakt, and Apple Health, emit a structured knowledge graph
capturing their skills, projects, experience, education, and interests as typed nodes with weighted edges.

You may call fetch_github_readme for up to 3 repositories to get richer project descriptions.
Once you have enough context, call emit_knowledge_graph with the final graph.

Rules:
- Node IDs: stable snake_case prefixed by type (e.g. skill-python, project-ml-tool)
- For interest nodes use: interest-{subtype}-{slugified-name} (e.g. interest-artist-kendrick-lamar, interest-genre-hip-hop)
- Infer skill nodes from GitHub languages and topics
- All cultural/media content uses type "interest" with metadata.subtype set to one of:
  artist, album, track, podcast, audiobook, movie, show, genre
- Emit up to 5 artist nodes, 3 album nodes, 5 podcast nodes, 2 audiobook nodes, 3-4 genre nodes
- Add movie/show nodes (as interest nodes with subtype movie/show) for Trakt history
- Add a health node if Apple Health data is present
- Always set metadata.url on every interest node where a URL is available
- Always set metadata.subtype on every interest node
- Connect skills to projects (used_in edges), interests to projects/skills (relates_to)
- Use relates_to edges between albums and their artists
- Use relates_to edges between podcasts/audiobooks and relevant skill or project nodes where a genuine connection exists
- Edge weight 0.0–1.0 based on relationship strength
- Prefer fewer accurate nodes over many speculative ones
"""
```

- [ ] **Step 5: Update the synthesizer context dict to include new Spotify fields**

In `synthesize_graph`, replace the `"spotify"` key in the `context` dict with:

```python
"spotify": {
    "top_artists": [{"name": a.name, "url": a.url, "genres": a.genres} for a in spotify.top_artists],
    "top_genres": spotify.top_genres,
    "top_tracks": [{"name": t.name, "artist": t.artist, "url": t.url} for t in spotify.top_tracks[:5]],
    "saved_shows": [{"name": s.name, "publisher": s.publisher, "url": s.url, "description": s.description} for s in spotify.saved_shows],
    "saved_audiobooks": [{"name": a.name, "author": a.author, "url": a.url} for a in spotify.saved_audiobooks],
    "recent_albums": [{"name": a.name, "artist": a.artist, "url": a.url} for a in spotify.recent_albums],
},
```

- [ ] **Step 6: Run synthesizer tests**

```bash
cd jobs/graph-gen && uv run pytest tests/test_synthesizer.py tests/test_synthesizer_agentic.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full test suite**

```bash
cd jobs/graph-gen && uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add jobs/graph-gen/synthesizer.py jobs/graph-gen/tests/test_synthesizer.py
git commit -m "feat(synthesizer): fold movie/show into interest subtype, add Spotify enrichment context"
```

---

## Task 3: Frontend — remove movie/show types, subtype-aware tooltip and sidebar

**Files:**
- Modify: `frontend/components/graph/ForceGraph.tsx`
- Modify: `frontend/components/graph/GraphSidebar.tsx`

There are no unit tests for these components. TypeScript compilation via `npm run build` is the verification step.

- [ ] **Step 1: Update `ForceGraph.tsx` — remove movie/show from type union and NODE_COLORS, update nodeLabel**

Open `frontend/components/graph/ForceGraph.tsx`. Make these three changes:

**1. Type union** (line ~8) — remove `"movie" | "show"`:
```ts
type: "skill" | "project" | "experience" | "education" | "interest" | "health";
```

**2. NODE_COLORS** — remove `movie` and `show` entries:
```ts
const NODE_COLORS: Record<GraphNode["type"], string> = {
  skill:      "#3b82f6",
  project:    "#34d399",
  experience: "#a78bfa",
  education:  "#fbbf24",
  interest:   "#f472b6",
  health:     "#4ade80",
};
```

**3. `nodeLabel` callback** — prefer `metadata.subtype` for the display label:
```ts
const nodeLabel = useCallback((node: GraphNode) => {
  const color = NODE_COLORS[node.type] ?? "#888";
  const subtype = node.metadata?.subtype as string | undefined;
  const raw = subtype ?? node.type;
  const display = raw.charAt(0).toUpperCase() + raw.slice(1);
  return `<span style="color:${color};font-weight:600">${display}</span><br/>${node.label}`;
}, []);
```

- [ ] **Step 2: Update `GraphSidebar.tsx` — show subtype in the red label**

Open `frontend/components/graph/GraphSidebar.tsx`. Add one line after `const url = ...` and update the `<p>` that renders `node.type`:

```tsx
const url = node.metadata?.url as string | undefined;
const displayType = (node.metadata?.subtype as string | undefined) ?? node.type;
```

Then replace the `<p>` tag that renders the type label:
```tsx
<p className="font-mono text-[#ef4444] text-xs tracking-widest uppercase mb-2">{displayType}</p>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/graph/ForceGraph.tsx frontend/components/graph/GraphSidebar.tsx
git commit -m "feat(frontend): subtype-aware tooltip and sidebar label, remove movie/show top-level types"
```

---

## Task 4: CI — trigger Cloud Run Job execution after image deploy

**Files:**
- Modify: `.github/workflows/deploy-job.yml`

- [ ] **Step 1: Add the execute step to `deploy-job.yml`**

Append a new step after the existing `Update Cloud Run Job image` step:

```yaml
      - name: Execute Cloud Run Job
        run: |
          gcloud run jobs execute graph-gen \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ vars.GCP_PROJECT_ID }} \
            --wait \
            --quiet
```

The `--wait` flag polls until the execution completes (or fails) and propagates the exit code to the workflow, so CI will turn red if the job errors.

The full updated `deploy-job.yml` after this change:

```yaml
name: Deploy Graph-Gen Job

on:
  push:
    branches: [main]
    paths:
      - "jobs/graph-gen/**"
      - ".github/workflows/deploy-job.yml"
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WIF_PROVIDER }}
          service_account: ${{ vars.WIF_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ vars.GCP_REGION }}-docker.pkg.dev --quiet

      - name: Build and push image
        run: |
          IMAGE=${{ vars.JOB_IMAGE }}:${{ github.sha }}
          docker build -t $IMAGE jobs/graph-gen/
          docker push $IMAGE
          docker tag $IMAGE ${{ vars.JOB_IMAGE }}:latest
          docker push ${{ vars.JOB_IMAGE }}:latest

      - name: Update Cloud Run Job image
        # Env vars and secrets are provisioned by Terraform (infra/) and persist across
        # image updates. This step only updates the container image — no --update-env-vars
        # needed here.
        run: |
          gcloud run jobs update graph-gen \
            --image ${{ vars.JOB_IMAGE }}:${{ github.sha }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ vars.GCP_PROJECT_ID }} \
            --quiet

      - name: Execute Cloud Run Job
        run: |
          gcloud run jobs execute graph-gen \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ vars.GCP_PROJECT_ID }} \
            --wait \
            --quiet
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy-job.yml
git commit -m "ci: execute graph-gen job after image deploy"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| `SavedShow`, `SavedAudiobook`, `RecentAlbum` dataclasses | Task 1, Step 4 |
| 3 new API fetches (shows, audiobooks, recently-played expanded to 50) | Task 1, Step 5 |
| Album deduplication on album.id | Task 1, Step 5 |
| `SpotifyData` 3 new fields with defaults | Task 1, Step 4 |
| Update `test_spotify.py` for new endpoints | Task 1, Step 3 |
| 3 new enriched Spotify tests | Task 1, Step 1 |
| GRAPH_TOOL enum drops movie/show | Task 2, Step 3 |
| SYSTEM_PROMPT subtype rules and caps (5 artists, 3 albums, 5 podcasts, 2 audiobooks, 3-4 genres) | Task 2, Step 4 |
| Synthesizer context gains saved_shows, saved_audiobooks, recent_albums | Task 2, Step 5 |
| ForceGraph: remove movie/show from type union and NODE_COLORS | Task 3, Step 1 |
| ForceGraph: subtype-aware nodeLabel tooltip | Task 3, Step 1 |
| GraphSidebar: show subtype in red label | Task 3, Step 2 |
| CI: trigger job execution after image deploy | Task 4 |

**Placeholder scan:** None found.

**Type consistency:** `SpotifyData.saved_shows` uses `list[SavedShow]` throughout. `SpotifyData.saved_audiobooks` uses `list[SavedAudiobook]` throughout. `SpotifyData.recent_albums` uses `list[RecentAlbum]` throughout. All match across Tasks 1 and 2.

**Note on `short_term` vs `medium_term`:** Task 1 switches `top/artists` and `top/tracks` from `medium_term` (6 months) to `short_term` (4 weeks) to better reflect "currently listening to." This is intentional per the brainstorm but will change which artists/tracks appear in the graph.
