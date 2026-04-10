# Phase 1.5C — Frontend SPA Redesign Design

**Date:** 2026-04-10

## Goal

Redesign the homepage as a single-page scrollable SPA with three sections: Hero (intro + expandable graph), About (bio + Currently block + activity feed), Writing (blog post cards). Fix two graph UX bugs: node click restarting the simulation, and missing reset-to-fit button.

## Architecture

All changes are in `frontend/`. The homepage (`app/page.tsx`) becomes a single-page layout composed of three full-width sections. A sticky nav provides anchor-link navigation. The backend gains a `GET /api/currently` endpoint that reads `currently.json` from GCS — the `CurrentlyBlock` component fetches it client-side and renders gracefully if the file doesn't exist yet (Plan B writes it).

## Layout

```
┌─────────────────────────────────────────┐
│  [sticky nav]  About · Writing          │
├───────────────────┬─────────────────────┤
│  HERO             │  GRAPH    [↺] [⤢]   │
│  name             │                     │
│  intro text       │  force graph        │
│                   │                     │
├───────────────────┴─────────────────────┤  id="about"
│  BIO + CURRENTLY        │  ACTIVITY     │
│  static bio paragraph   │  feed         │
│  ─────────────────      │               │
│  Working on: ...        │               │
│  Listening: ...         │               │
│  Playing:   ...         │               │
│  Watching:  ...         │               │
├─────────────────────────────────────────┤  id="writing"
│  WRITING                                │
│  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │ card │  │ card │  │ card │          │
│  └──────┘  └──────┘  └──────┘          │
└─────────────────────────────────────────┘
```

## Component Map

```
frontend/
├── app/
│   └── page.tsx                     # Compose all sections, remove old layout
├── components/
│   ├── nav/
│   │   └── SiteNav.tsx              # Sticky top nav, anchor links to #about #writing
│   ├── hero/
│   │   └── HeroSection.tsx          # Two-column: intro text left, GraphPanel right
│   ├── graph/
│   │   ├── GraphPanel.tsx           # Expand/collapse overlay, reset button, fixed bugs
│   │   └── ForceGraph.tsx           # Two fixes: cooldownTicks=0, memoized callbacks
│   ├── about/
│   │   ├── AboutSection.tsx         # Two-column: bio+currently left, activity right
│   │   ├── CurrentlyBlock.tsx       # GET /api/currently, renders rows, null-safe
│   │   └── ActivityFeed.tsx         # Moved from old homepage, no logic changes
│   └── writing/
│       └── WritingSection.tsx       # getAllPosts(), renders PostCard grid
└── (existing blog routes unchanged)
```

## Graph Fixes

### Node click reorganizing nodes
**Cause:** clicking a node updates `activeNodeIds` state in a parent, new prop reference passed to `<ForceGraph2D />` restarts force simulation.
**Fix:**
- Memoize all graph callbacks (`nodeColor`, `onNodeClick`, `linkColor`) with `useCallback` and stable deps
- Set `onEngineStop` callback to call `graphRef.current.d3ReheatSimulation = () => {}` — after initial layout, freeze the simulation so re-renders don't restart physics
- Alternatively: `cooldownTicks={Infinity}` until first `onEngineStop`, then set to `0` via ref

### Reset button
- `graphRef: React.MutableRefObject<ForceGraphMethods>` passed to `<ForceGraph2D ref={graphRef} />`
- Reset button calls `graphRef.current.zoomToFit(400)`
- Positioned top-right of graph panel alongside expand button

### Expand/collapse
- Default: graph fills right half of hero (`~50vw`, `70vh`)
- Expanded: fixed overlay `100vw × 100vh`, `z-index: 50`, CSS transition on width/height
- Toggle button top-right corner; ESC key also collapses

## `currently.json` Schema (contract for Plan B)

```json
{
  "generated_at": "2026-04-10T06:00:00Z",
  "working_on": [
    { "name": "tapshalkar.com", "url": "https://github.com/adityataps/tapshalkar.com" }
  ],
  "listening_to": { "artist": "Kendrick Lamar", "track": "GNX", "url": "https://open.spotify.com/..." },
  "playing": { "name": "Elden Ring", "hours": 47, "url": "https://store.steampowered.com/app/1245620" },
  "watching": { "title": "Severance", "season": 2, "url": "https://trakt.tv/..." }
}
```

All fields optional — `CurrentlyBlock` renders only fields present.

## Backend Addition

`backend/app/routers/currently.py` — `GET /api/currently`:
- Calls `core.gcs.fetch_object(settings.gcs_bucket, "currently.json")`
- Returns parsed JSON with `Cache-Control: public, max-age=300`
- Returns `404` if object not found (Plan B hasn't run yet)
- Returns `502` on GCS error

Registered in `main.py` under `/api` prefix.
