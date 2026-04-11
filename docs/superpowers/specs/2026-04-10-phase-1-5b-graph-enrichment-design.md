# Phase 1.5B — Graph Enrichment & Agentic Synthesizer Design

**Date:** 2026-04-10

## Goal

Enrich the knowledge graph with richer metadata (links, stats, achievements), add two new data sources (Trakt.tv, Apple Health), rewrite the synthesizer as an agentic Claude loop with tools, and write `currently.json` to GCS for the frontend `CurrentlyBlock`.

## Architecture

The graph-gen job gains two new gatherers and enriches existing ones. The synthesizer is rewritten: instead of a single `emit_knowledge_graph` tool call, Claude runs a tool-use loop where it can call enrichment tools (e.g. `fetch_github_readme`) before emitting the final graph. All gatherers now return metadata fields alongside their core data. The job also writes `currently.json` to GCS after graph synthesis.

## Data Sources

### Existing — enriched

| Source | New metadata |
|--------|-------------|
| GitHub | `html_url` (repo link), `description`, `language`, `stars` |
| Spotify | `external_urls.spotify` for artists and tracks |
| Steam | `store_url` (`store.steampowered.com/app/{appid}`), `hours_played`, top achievements |

### New — Trakt.tv

OAuth (client credentials + refresh token). Fetches:
- Watch history (movies + shows, last 50)
- Watchlist (plan to watch)
- Currently watching (in-progress shows)

Produces nodes of type `movie` and `show` with metadata: title, year, Trakt URL, genres, rating.

### New — Apple Health

Reads JSON files from `gs://adits-gcp-static-site/data/ephemeral/apple-health/` (written by Health Auto Export iOS app). Extracts summary metrics: steps, active energy, sleep, workouts. Produces a single `health` node or enriches an existing `me` node's metadata.

## Agentic Synthesizer

Claude runs a tool-use loop with two tools:

| Tool | Purpose |
|------|---------|
| `fetch_github_readme(owner, repo)` | Fetches README via GitHub API for a repo — used to write richer node descriptions |
| `emit_knowledge_graph(nodes, edges)` | Terminal tool — Claude calls this to submit the final graph |

Flow:
1. All gathered data (GitHub, Spotify, Steam, Trakt, Apple Health) passed as context in system prompt
2. Claude decides which repos warrant README enrichment, calls `fetch_github_readme` as needed
3. Claude calls `emit_knowledge_graph` with fully enriched nodes + edges
4. Max 10 tool call iterations to bound cost and time

## `currently.json`

Written to `gs://adits-gcp-static-site/currently.json` after synthesis. Schema:

```json
{
  "generated_at": "2026-04-10T06:00:00Z",
  "working_on": [{ "name": "tapshalkar.com", "url": "https://github.com/adityataps/tapshalkar.com" }],
  "listening_to": { "artist": "Kendrick Lamar", "track": "GNX", "url": "https://open.spotify.com/..." },
  "playing": { "name": "Elden Ring", "hours": 47, "url": "https://store.steampowered.com/app/1245620" },
  "watching": { "title": "Severance", "season": 2, "url": "https://trakt.tv/..." }
}
```

Derived from gathered data — no LLM generation.

## Infrastructure Changes

### GCS lifecycle rule (`infra/gcs.tf`)

Add lifecycle rule scoped to `data/ephemeral/` prefix: delete objects after 365 days.

### New secrets (`infra/secrets.tf` + Secret Manager)

- `trakt-client-id`
- `trakt-client-secret`
- `trakt-refresh-token`

### Cloud Run Job env vars (`infra/cloud_run_job.tf`)

Wire the three Trakt secrets into the job container.

## File Map

```
jobs/graph-gen/
├── gatherers/
│   ├── github.py          # update: add html_url, description, language, stars to node metadata
│   ├── spotify.py         # update: add external_urls.spotify to artist/track nodes
│   ├── steam.py           # update: add store_url, hours_played, achievements to game nodes
│   ├── trakt.py           # new: OAuth refresh + history/watchlist/currently-watching
│   └── apple_health.py    # new: reads latest JSON from GCS prefix, returns summary metrics
├── synthesizer.py         # rewrite: agentic loop — fetch_github_readme + emit_knowledge_graph tools
├── writer.py              # update: write currently.json alongside graph.json
├── main.py                # update: call new gatherers, pass Apple Health data to synthesizer
├── config.py              # update: add TRAKT_* and APPLE_HEALTH_PREFIX settings

infra/
├── gcs.tf                 # add lifecycle rule for data/ephemeral/ prefix
├── secrets.tf             # add trakt-client-id, trakt-client-secret, trakt-refresh-token
└── cloud_run_job.tf       # wire Trakt secrets into job env
```
