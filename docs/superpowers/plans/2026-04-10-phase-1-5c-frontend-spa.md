# Phase 1.5C — Frontend SPA Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the homepage as a single-page scrollable SPA with three sections (Hero + graph, About + activity, Writing cards). Fix graph node-click reorganization bug. Add graph reset-to-fit and fullscreen expand. Add `/api/currently` backend endpoint.

**Architecture:** `app/page.tsx` becomes a single-page layout composed of three section components. New sticky nav provides anchor-link scroll. `GraphPanel` gains expand/collapse overlay and reset button. `ForceGraph` is fixed to freeze simulation after initial layout so re-renders don't restart physics. `CurrentlyBlock` fetches `/api/currently` client-side and renders gracefully when endpoint returns 404 (data not populated until Plan B). Backend gains a new `currently` router.

**Tech Stack:** Next.js 15 App Router, React, Tailwind CSS v4, react-force-graph-2d, FastAPI

**Prerequisites:** Phase 1 frontend complete, Phase 1.5A subdomain routing complete (CORS fix needed for graph to load on subdomain).

---

## File Map

```
frontend/
├── app/
│   └── page.tsx                          # Rewrite: compose all sections
├── components/
│   ├── nav/
│   │   └── SiteNav.tsx                   # New: sticky nav with anchor links
│   ├── hero/
│   │   └── HeroSection.tsx              # New: two-column intro + graph
│   ├── graph/
│   │   ├── GraphPanel.tsx               # Update: expand/collapse, reset button
│   │   └── ForceGraph.tsx               # Fix: cooldown, memoized callbacks
│   ├── about/
│   │   ├── AboutSection.tsx             # New: two-column bio+currently / activity
│   │   ├── CurrentlyBlock.tsx           # New: fetches /api/currently
│   │   └── ActivityFeed.tsx             # Move from existing location
│   └── writing/
│       └── WritingSection.tsx           # New: card grid of blog posts

backend/
└── app/
    ├── routers/
    │   └── currently.py                 # New: GET /api/currently
    └── main.py                          # Register currently router
```

---

## Task 1: Backend — `/api/currently` Endpoint

- [ ] **Step 1: Write failing test `backend/tests/test_currently.py`**

```python
import json
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app import core

SAMPLE_CURRENTLY = {
    "generated_at": "2026-04-10T06:00:00Z",
    "working_on": [{"name": "tapshalkar.com", "url": "https://github.com/adityataps/tapshalkar.com"}],
    "listening_to": {"artist": "Kendrick Lamar", "track": "GNX", "url": "https://open.spotify.com/track/123"},
}


@pytest.mark.anyio
async def test_currently_returns_json():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        return json.dumps(SAMPLE_CURRENTLY).encode()

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/currently")

    assert response.status_code == 200
    assert response.json()["working_on"][0]["name"] == "tapshalkar.com"


@pytest.mark.anyio
async def test_currently_returns_404_when_not_found():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        from google.cloud.exceptions import NotFound
        raise NotFound("currently.json not found")

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/currently")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_currently_returns_502_on_gcs_error():
    async def mock_fetch(_bucket: str, _key: str) -> bytes:
        raise Exception("GCS unavailable")

    with patch.object(core.gcs, "fetch_object", side_effect=mock_fetch):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/currently")

    assert response.status_code == 502
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd backend
uv run pytest tests/test_currently.py -v
```

Expected: `FAILED` — no route `/api/currently`

- [ ] **Step 3: Create `backend/app/routers/currently.py`**

```python
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from google.cloud.exceptions import NotFound

from app import core
from app.config import settings

router = APIRouter()


@router.get("/currently")
async def get_currently() -> JSONResponse:
    try:
        data = await core.gcs.fetch_object(settings.gcs_bucket, "currently.json")
    except NotFound:
        raise HTTPException(status_code=404, detail="Currently data not available yet")
    except Exception:
        raise HTTPException(status_code=502, detail="Currently data unavailable")

    return JSONResponse(
        content=json.loads(data),
        headers={"Cache-Control": "public, max-age=300"},
    )
```

- [ ] **Step 4: Register router in `backend/app/main.py`**

Read `backend/app/main.py`. Add import and registration:

```python
from app.routers import health, graph, contact, currently
# ...
app.include_router(currently.router, prefix="/api")
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
uv run pytest tests/test_currently.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): /api/currently endpoint"
```

---

## Task 2: Fix ForceGraph — Freeze Simulation + Memoize Callbacks

- [ ] **Step 1: Read `frontend/components/graph/ForceGraph.tsx`**

- [ ] **Step 2: Update `ForceGraph.tsx`**

Apply two fixes:
1. Track whether the engine has settled with a ref; set `cooldownTicks={0}` after first `onEngineStop` to freeze physics
2. Wrap `nodeColor` and `onNodeClick` in `useCallback` with stable deps

```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";

interface GraphNode {
  id: string;
  type: string;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface ForceGraphProps {
  data: GraphData;
  activeNodeIds?: string[];
  graphRef: React.MutableRefObject<ForceGraphMethods | undefined>;
}

export default function ForceGraph({ data, activeNodeIds = [], graphRef }: ForceGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const settled = useRef(false);
  const [cooldownTicks, setCooldownTicks] = useState<number | undefined>(undefined);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const nodeColor = useCallback(
    (node: GraphNode) =>
      activeNodeIds.includes(node.id) ? "#ef4444" : "#444444",
    [activeNodeIds]
  );

  const handleEngineStop = useCallback(() => {
    if (!settled.current) {
      settled.current = true;
      setCooldownTicks(0);
      graphRef.current?.zoomToFit(400);
    }
  }, [graphRef]);

  const graphData = {
    nodes: data.nodes,
    links: data.edges.map((e) => ({ source: e.source, target: e.target })),
  };

  return (
    <div ref={containerRef} className="w-full h-full">
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel="label"
        nodeColor={nodeColor}
        cooldownTicks={cooldownTicks}
        onEngineStop={handleEngineStop}
        backgroundColor="#0d0d0d"
      />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/graph/ForceGraph.tsx
git commit -m "fix(frontend): freeze graph simulation after layout, memoize callbacks"
```

---

## Task 3: Update GraphPanel — Expand/Collapse + Reset Button

- [ ] **Step 1: Read `frontend/components/graph/GraphPanel.tsx`**

- [ ] **Step 2: Rewrite `GraphPanel.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { ForceGraphMethods } from "react-force-graph-2d";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

interface GraphNode {
  id: string;
  type: string;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphPanelProps {
  activeNodeIds?: string[];
}

export default function GraphPanel({ activeNodeIds = [] }: GraphPanelProps) {
  const [data, setData] = useState<GraphData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const graphRef = useRef<ForceGraphMethods>();

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/graph`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleReset = () => graphRef.current?.zoomToFit(400);

  const panelClass = expanded
    ? "fixed inset-0 z-50 bg-[#0d0d0d] transition-all duration-300"
    : "relative w-full h-full";

  return (
    <div className={panelClass}>
      <div className="absolute top-2 right-2 z-10 flex gap-2">
        <button
          onClick={handleReset}
          className="text-[#444444] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
          title="Reset view"
        >
          ↺
        </button>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="text-[#444444] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
          title={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? "⊠" : "⤢"}
        </button>
      </div>

      {data ? (
        <ForceGraph data={data} activeNodeIds={activeNodeIds} graphRef={graphRef} />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-[#444444] text-sm">
          loading graph...
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/graph/GraphPanel.tsx
git commit -m "feat(frontend): graph expand/collapse overlay and reset button"
```

---

## Task 4: SiteNav Component

- [ ] **Step 1: Create `frontend/components/nav/SiteNav.tsx`**

```tsx
"use client";

export default function SiteNav() {
  return (
    <nav className="sticky top-0 z-40 flex items-center justify-between px-8 py-4 bg-[#0d0d0d]/90 backdrop-blur border-b border-[#1a1a1a]">
      <a href="/" className="font-serif text-[#f5f5f0] text-sm tracking-wide">
        aditya tapshalkar
      </a>
      <div className="flex gap-6">
        <a href="#about" className="text-[#444444] hover:text-[#f5f5f0] text-sm transition-colors">
          About
        </a>
        <a href="#writing" className="text-[#444444] hover:text-[#f5f5f0] text-sm transition-colors">
          Writing
        </a>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/nav/SiteNav.tsx
git commit -m "feat(frontend): sticky site nav with anchor links"
```

---

## Task 5: HeroSection Component

- [ ] **Step 1: Create `frontend/components/hero/HeroSection.tsx`**

```tsx
import GraphPanel from "@/components/graph/GraphPanel";

export default function HeroSection() {
  return (
    <section className="flex flex-col md:flex-row min-h-[80vh]">
      <div className="flex flex-col justify-center px-8 md:px-16 py-16 md:w-1/2">
        <h1 className="font-serif text-4xl md:text-5xl text-[#f5f5f0] mb-4">
          Aditya Tapshalkar
        </h1>
        <p className="text-[#444444] text-lg leading-relaxed max-w-md">
          Software engineer. Building things at the intersection of systems and
          intelligence.
        </p>
      </div>
      <div className="md:w-1/2 min-h-[60vh] md:min-h-0">
        <GraphPanel />
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/hero/HeroSection.tsx
git commit -m "feat(frontend): hero section with intro and graph"
```

---

## Task 6: CurrentlyBlock Component

- [ ] **Step 1: Create `frontend/components/about/CurrentlyBlock.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";

interface Currently {
  generated_at?: string;
  working_on?: { name: string; url: string }[];
  listening_to?: { artist: string; track: string; url: string };
  playing?: { name: string; hours: number; url: string };
  watching?: { title: string; season?: number; url?: string };
}

export default function CurrentlyBlock() {
  const [data, setData] = useState<Currently | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/currently`)
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((d) => d && setData(d))
      .catch(() => {});
  }, []);

  if (!data) return null;

  return (
    <div className="mt-6">
      <p className="text-[#444444] text-xs uppercase tracking-widest mb-3">Currently</p>
      <div className="flex flex-col gap-2 text-sm">
        {data.working_on?.map((p) => (
          <Row key={p.name} label="Working on" value={p.name} url={p.url} />
        ))}
        {data.listening_to && (
          <Row
            label="Listening to"
            value={`${data.listening_to.artist} · ${data.listening_to.track}`}
            url={data.listening_to.url}
          />
        )}
        {data.playing && (
          <Row
            label="Playing"
            value={`${data.playing.name} · ${data.playing.hours}h`}
            url={data.playing.url}
          />
        )}
        {data.watching && (
          <Row
            label="Watching"
            value={data.watching.season ? `${data.watching.title} S${data.watching.season}` : data.watching.title}
            url={data.watching.url}
          />
        )}
      </div>
    </div>
  );
}

function Row({ label, value, url }: { label: string; value: string; url?: string }) {
  return (
    <div className="flex gap-3">
      <span className="text-[#444444] w-28 shrink-0">{label}</span>
      {url ? (
        <a href={url} target="_blank" rel="noopener noreferrer" className="text-[#f5f5f0] hover:text-[#ef4444] transition-colors">
          {value}
        </a>
      ) : (
        <span className="text-[#f5f5f0]">{value}</span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/about/CurrentlyBlock.tsx
git commit -m "feat(frontend): CurrentlyBlock component"
```

---

## Task 7: AboutSection Component

- [ ] **Step 1: Locate existing ActivityFeed component**

```bash
find frontend/components -name "*.tsx" | head -30
```

Note the current path of the ActivityFeed component.

- [ ] **Step 2: Create `frontend/components/about/AboutSection.tsx`**

Update the import path for ActivityFeed to match its actual location found in Step 1.

```tsx
import CurrentlyBlock from "./CurrentlyBlock";
import ActivityFeed from "./ActivityFeed";  // update path if needed

export default function AboutSection() {
  return (
    <section id="about" className="flex flex-col md:flex-row gap-12 px-8 md:px-16 py-16 border-t border-[#1a1a1a]">
      <div className="md:w-1/2">
        <h2 className="font-serif text-2xl text-[#f5f5f0] mb-4">About</h2>
        <p className="text-[#444444] leading-relaxed">
          {/* Replace with your actual bio */}
          I'm a software engineer based in New York. I build systems that are fast,
          reliable, and occasionally interesting. Currently working on making this
          site a live reflection of what I'm up to.
        </p>
        <CurrentlyBlock />
      </div>
      <div className="md:w-1/2">
        <ActivityFeed />
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Move ActivityFeed if needed**

If ActivityFeed is not already at `frontend/components/about/ActivityFeed.tsx`, copy it there and update its import in AboutSection. Do not delete the original until page.tsx is updated.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/about/
git commit -m "feat(frontend): about section with bio, currently, and activity feed"
```

---

## Task 8: WritingSection Component

- [ ] **Step 1: Create `frontend/components/writing/WritingSection.tsx`**

```tsx
import Link from "next/link";
import { getAllPosts } from "@/app/blog/utils";

export default function WritingSection() {
  const posts = getAllPosts();

  return (
    <section id="writing" className="px-8 md:px-16 py-16 border-t border-[#1a1a1a]">
      <h2 className="font-serif text-2xl text-[#f5f5f0] mb-8">Writing</h2>
      {posts.length === 0 ? (
        <p className="text-[#444444] text-sm">No posts yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group flex flex-col gap-2 p-5 border border-[#1a1a1a] hover:border-[#444444] transition-colors"
            >
              <span className="text-[#444444] text-xs">{post.date}</span>
              <h3 className="font-serif text-[#f5f5f0] group-hover:text-[#ef4444] transition-colors">
                {post.title}
              </h3>
              {post.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-auto pt-3">
                  {post.tags.map((tag) => (
                    <span key={tag} className="text-[#444444] text-xs">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/writing/WritingSection.tsx
git commit -m "feat(frontend): writing section with blog post cards"
```

---

## Task 9: Compose Homepage

- [ ] **Step 1: Read `frontend/app/page.tsx`**

- [ ] **Step 2: Rewrite `frontend/app/page.tsx`**

```tsx
import SiteNav from "@/components/nav/SiteNav";
import HeroSection from "@/components/hero/HeroSection";
import AboutSection from "@/components/about/AboutSection";
import WritingSection from "@/components/writing/WritingSection";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0d0d0d]">
      <SiteNav />
      <HeroSection />
      <AboutSection />
      <WritingSection />
    </main>
  );
}
```

- [ ] **Step 3: Run local dev server and verify layout**

```bash
cd frontend
npm run dev
```

Visit `http://localhost:3000`. Expected:
- Sticky nav visible, links scroll to `#about` and `#writing`
- Hero: intro text left, graph right
- Graph loads, nodes don't reorganize on click
- Reset (↺) and expand (⤢) buttons visible on graph
- About section: bio, Currently block (empty/hidden if no data), activity feed
- Writing section: card grid (empty if no posts)

- [ ] **Step 4: Verify graph expand**

Click ⤢ — graph should fill viewport. Press Escape or click ⊠ — should collapse back.

- [ ] **Step 5: Build to catch any static export errors**

```bash
npm run build
```

Expected: no errors, `out/` generated.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): SPA homepage with hero, about, and writing sections"
```

---

## Task 10: Push and Deploy

- [ ] **Step 1: Push all commits**

```bash
git push
```

- [ ] **Step 2: Watch GitHub Actions**

GitHub → Actions → Deploy Frontend and Deploy Backend should both go green.

- [ ] **Step 3: Smoke test on subdomain**

Visit `https://aditya.tapshalkar.com`. Expected:
- All three sections render
- Graph loads without CORS errors
- Expand/reset buttons work
- Blog cards show (if any posts exist)
- Currently block hidden (until Plan B runs graph-gen job)
