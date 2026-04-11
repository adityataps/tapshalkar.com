# Spotify Enrichment Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the knowledge graph with granular Spotify content — artists, albums, podcasts, audiobooks, and genres — using a type + subtype model where all media/cultural content is `type: "interest"` with a `metadata.subtype` discriminator.

**Architecture:** Extend `sources/spotify.py` with three new API calls (saved shows, saved audiobooks, expanded recently-played). Pass enriched data to the existing agentic synthesizer, which emits `interest` nodes with subtypes. Update the frontend to display subtypes in tooltips and the sidebar.

**Tech Stack:** Python 3.13, httpx, Spotify Web API, Claude API (synthesizer), Next.js / TypeScript (frontend)

---

## Data Model

### New node subtype system

All cultural/media content uses `type: "interest"` with `metadata.subtype` set to one of:

| subtype | description | example id |
|---|---|---|
| `artist` | Music artist | `interest-artist-kendrick-lamar` |
| `album` | Music album | `interest-album-to-pimp-a-butterfly` |
| `track` | Individual song | `interest-track-humble` |
| `podcast` | Podcast show | `interest-podcast-lex-fridman` |
| `audiobook` | Audiobook | `interest-audiobook-atomic-habits` |
| `movie` | Film (existing, migrated) | `interest-movie-dune` |
| `show` | TV show (existing, migrated) | `interest-show-the-wire` |
| `genre` | Music genre | `interest-genre-hip-hop` |

**Node ID convention:** `interest-{subtype}-{slugified-name}` (all lowercase, hyphens for spaces).

`movie` and `show` are migrated from top-level types into `interest` subtypes. The top-level type enum shrinks to:
```
["skill", "project", "experience", "education", "interest", "health"]
```

### New dataclasses (`sources/spotify.py`)

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

`SpotifyData` gains three new fields:
```python
@dataclass
class SpotifyData:
    top_artists: list[TopArtist]
    top_tracks: list[TopTrack]
    top_genres: list[str]
    recently_played: list[RecentTrack]
    saved_shows: list[SavedShow]        # new
    saved_audiobooks: list[SavedAudiobook]  # new
    recent_albums: list[RecentAlbum]    # new
```

---

## Data Fetching (`sources/spotify.py`)

Three new endpoints added to the existing `asyncio.gather` call:

| Endpoint | Params | Purpose |
|---|---|---|
| `GET /v1/me/shows` | `limit=10` | Saved/followed podcasts |
| `GET /v1/me/audiobooks` | `limit=10` | Saved audiobooks |
| `GET /v1/me/player/recently-played` | `limit=50` (up from 10) | More coverage for album extraction |

Albums are extracted from recently-played by deduplicating on `track.album.id`, keeping the album name, primary artist, and Spotify URL. The first 10 unique albums are kept. The `recently_played` field on `SpotifyData` will now contain up to 50 `RecentTrack` items instead of 10; downstream consumers (`_build_activity_feed` in `main.py`) already slice with `[:5]` so this is non-breaking.

---

## Synthesizer (`synthesizer.py`)

### Updated GRAPH_TOOL schema

The `type` enum changes to:
```json
["skill", "project", "experience", "education", "interest", "health"]
```

### Updated SYSTEM_PROMPT additions

Claude is instructed to:
- Emit up to **5 artist nodes**, **3 album nodes**, **5 podcast nodes**, **2 audiobook nodes**, **3–4 genre nodes** as `interest` nodes
- Always set `metadata.subtype` on every interest node
- Always set `metadata.url` on every interest node where a URL is available
- Use `relates_to` edges between albums and their artists
- Use `relates_to` edges between podcasts/audiobooks and relevant skill or project nodes where a genuine connection exists (e.g. an ML podcast → `skill-python`)
- Migrate any existing `movie`/`show` nodes to `type: "interest"` with the appropriate subtype

### Updated synthesizer context

```python
"spotify": {
    "top_artists": [...],         # existing
    "top_genres": [...],          # existing
    "top_tracks": [...],          # existing
    "saved_shows": [
        {"name": ..., "publisher": ..., "url": ..., "description": ...},
        ...
    ],
    "saved_audiobooks": [
        {"name": ..., "author": ..., "url": ...},
        ...
    ],
    "recent_albums": [
        {"name": ..., "artist": ..., "url": ...},
        ...
    ],
}
```

---

## Frontend

### `ForceGraph.tsx`

- Remove `"movie"` and `"show"` from the `GraphNode` type union
- Remove `movie` and `show` entries from `NODE_COLORS`
- Update the `nodeLabel` callback to prefer `metadata.subtype` over `node.type` for the colored label:

```ts
const nodeLabel = useCallback((node: GraphNode) => {
  const color = NODE_COLORS[node.type] ?? "#888";
  const subtype = node.metadata?.subtype as string | undefined;
  const typeLabel = (subtype ?? node.type);
  const display = typeLabel.charAt(0).toUpperCase() + typeLabel.slice(1);
  return `<span style="color:${color};font-weight:600">${display}</span><br/>${node.label}`;
}, []);
```

### `GraphSidebar.tsx`

- The red label at the top currently shows `node.type`. Update to prefer `metadata.subtype`:

```tsx
const displayType = (node.metadata?.subtype as string | undefined) ?? node.type;
// render displayType instead of node.type
```

---

## Testing

### `tests/test_spotify_enriched.py` (new)

- `test_fetch_spotify_includes_saved_shows` — mock `/v1/me/shows`, assert `saved_shows[0].name` and `url` are populated
- `test_fetch_spotify_includes_audiobooks` — mock `/v1/me/audiobooks`, assert `saved_audiobooks[0].name` and `author` are populated
- `test_fetch_spotify_extracts_recent_albums` — mock recently-played with 3 tracks across 2 albums, assert `recent_albums` has 2 deduplicated entries

### `tests/test_synthesizer.py` (update)

- Update fixtures to pass `saved_shows=[]`, `saved_audiobooks=[]`, `recent_albums=[]` to `SpotifyData`
- Update the mock `emit_knowledge_graph` call to use `type: "interest"` instead of `"movie"` / `"show"` where applicable

---

## Files Changed

| File | Change |
|---|---|
| `jobs/graph-gen/sources/spotify.py` | 3 new fetches, 3 new dataclasses, expand recently-played to 50, album deduplication |
| `jobs/graph-gen/synthesizer.py` | Fold movie/show into interest, add subtype guidance, pass new context fields |
| `jobs/graph-gen/tests/test_spotify_enriched.py` | New: 3 tests for new fetches |
| `jobs/graph-gen/tests/test_synthesizer.py` | Update SpotifyData fixtures for new fields |
| `frontend/components/graph/ForceGraph.tsx` | Remove movie/show types, subtype-aware tooltip |
| `frontend/components/graph/GraphSidebar.tsx` | Show subtype label |

No infrastructure changes required.