# tapshalkar.com — Portfolio Site Design Spec

**Date:** 2026-04-09
**Status:** Approved
**Phase:** 1 (core portfolio)

---

## Overview

Personal portfolio site for Aditya Tapshalkar, ML/AI engineer. Monorepo covering frontend, backend API, a scheduled AI-driven knowledge graph generation job, and GCP infrastructure managed with Terraform.

Phase 2 (not in scope here) adds a "digital me" agentic chatbot powered by Claude, using the knowledge graph as its knowledge base.

---

## Architecture

### Topology

```
Browser
  → Cloud CDN + Load Balancer
      → GCS bucket          (Next.js static export — HTML/CSS/JS)
      → Cloud Run (FastAPI)  (graph API + contact form)

Cloud Scheduler (daily cron)
  → Cloud Run Job (graph-gen)
      → GitHub API, Spotify API, Steam API  (parallel fetch)
      → Claude API                          (graph synthesis)
      → GCS bucket                          (writes graph.json, activity-feed.json, now.json)
      → Cloud CDN cache invalidation

Obsidian (local vault)
  → GitHub (git sync plugin)
  → GitHub Actions
      → next build (reads markdown from repo)
      → gsutil rsync → GCS bucket

Terraform (infra/)
  → GCS, Cloud CDN, Cloud Run service, Cloud Run Job,
     Cloud Scheduler, Artifact Registry, IAM, Secret Manager resources
```

### GCP Services

| Service | Purpose |
|---|---|
| Cloud Storage (GCS) | Hosts static site + generated JSON files |
| Cloud CDN + Load Balancer | CDN layer, TLS termination, routes `/api/*` to Cloud Run |
| Cloud Run (service) | FastAPI backend — graph proxy + contact form |
| Cloud Run (job) | graph-gen — scheduled data pipeline |
| Cloud Scheduler | Triggers graph-gen job daily at 06:00 UTC |
| Artifact Registry | Stores Docker images for Cloud Run service + job |
| Secret Manager | Stores API keys — injected into Cloud Run at runtime |
| Workload Identity Federation | Keyless auth for GitHub Actions → GCP |

### DNS

Domain registered externally. DNS to be migrated to Cloudflare (free). FQDN pointed at the Cloud CDN load balancer IP. Decision deferred — Terraform outputs the load balancer IP for manual DNS wiring.

---

## Frontend (Next.js)

### Pages

| Route | Description |
|---|---|
| `/` | Split hero (text left, force-directed graph right), activity feed, recent posts, contact CTA |
| `/blog` | Post index, dark editorial list |
| `/blog/[slug]` | Rendered markdown post, read time, tag links |
| `/about` | Bio, social links, experience/education timeline |

### Knowledge Graph Component

- Library: `react-force-graph-2d` (D3-backed, React wrapper)
- Must be loaded client-side only: `dynamic(() => import(...), { ssr: false })`
- Data: fetched from `GET /api/graph` on mount — never bundled at build time
- Node types: `skill | project | experience | education | interest`
- Node IDs: stable snake_case strings (e.g. `skill-python`, `project-xyz`) — required for Phase 2 agent highlighting
- Props include `activeNodeIds: string[]` — highlights nodes by ID (used by Phase 2 agent; wired but inactive in Phase 1)
- Interactions: click node → sidebar drawer with entity details; toggle buttons to filter by node type

### Blog Pipeline

- Obsidian git-syncs markdown into `frontend/content/blog/`
- Parsed with `next-mdx-remote` (contentlayer is unmaintained)
- `generateStaticParams` at build time — one pre-rendered HTML per post
- Frontmatter: `title`, `date`, `tags`, `draft` (drafts excluded from build)

### Static Export

```ts
// next.config.ts
output: 'export'
images: { unoptimized: true }
```

### Design Tokens

```
bg:           #0d0d0d
text:         #f5f5f0
muted:        #444444
accent:       #ef4444   (red — primary interactive + label color)
font-serif:   Georgia
font-mono:    'Courier New'
```

Landing page hero: split layout — serif/monospace text on left, force-directed graph on right.
Monospace used only for eyebrow labels and technical metadata, not body text.

---

## Backend (FastAPI)

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Cloud Run health check |
| `GET` | `/graph` | Fetches `graph.json` from GCS, returns to client |
| `POST` | `/contact` | Accepts `{name, email, message}`, sends via Resend API |

`/graph` proxies GCS rather than exposing the bucket publicly — preserves ability to add auth/caching later.

`/contact` is rate-limited via `slowapi`.

CORS restricted to the production frontend origin + localhost for dev.

### Runtime

- Python 3.13-slim, uv
- `uvicorn` single worker (Cloud Run handles horizontal scaling)
- Cloud Run min-instances: `0` (cold starts acceptable for a portfolio)
- Secrets: all via Secret Manager env var bindings in Cloud Run service definition

### Dockerfile pattern

```dockerfile
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Graph-Gen Job (Cloud Run Job)

### Pipeline

```
1. Fetch APIs concurrently (asyncio.gather):
     - GitHub: repos, languages, pinned READMEs, contribution stats
     - Spotify: top artists/tracks/genres, recently played
     - Steam: game library, recent playtime

2. Synthesize via Claude API (structured output via tool use):
     System prompt instructs Claude to emit typed nodes + weighted edges.
     Node types: skill | project | experience | education | interest
     Edge types: used_in | worked_on | studied_at | interested_in | relates_to
     All node IDs must be stable snake_case strings.

3. Write to GCS:
     - graph.json          (nodes + edges)
     - activity-feed.json  (recent GitHub commits, Spotify plays, Steam sessions)
     - now.json            (/now page snapshot)

4. Invalidate Cloud CDN cache for updated paths.
```

### Secrets Required

| Secret | Source |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic console |
| `SPOTIFY_CLIENT_ID` | Spotify developer dashboard |
| `SPOTIFY_CLIENT_SECRET` | Spotify developer dashboard |
| `SPOTIFY_REFRESH_TOKEN` | OAuth flow (one-time setup) |
| `STEAM_API_KEY` | Steam developer portal |
| `GITHUB_TOKEN` | GitHub PAT (read-only, public repos) |

### Schedule

`0 6 * * *` — daily at 06:00 UTC. Configurable via Terraform variable `graph_gen_schedule`.

---

## Secrets Management

- All secrets stored in **Google Secret Manager**
- Secret Manager *resources* managed by Terraform; values populated manually via `gcloud secrets versions add`
- Cloud Run service + job: secrets bound as env vars in resource definition (never in image)
- IAM: Cloud Run service accounts granted `secretmanager.secretAccessor` — Terraform-managed
- GitHub Actions: Workload Identity Federation — no long-lived JSON keys in GitHub Secrets
- Local dev: `.env` file (gitignored); `.env.example` committed with key names, no values

---

## CI/CD (GitHub Actions)

Three workflows, each path-scoped:

| Workflow | Trigger path | Steps |
|---|---|---|
| `deploy-frontend.yml` | `frontend/**` | `npm ci` → `next build` → `gsutil rsync out/ gs://$BUCKET/` → CDN invalidate |
| `deploy-backend.yml` | `backend/**` | `docker build` → push to Artifact Registry → `gcloud run deploy` |
| `deploy-job.yml` | `jobs/graph-gen/**` | `docker build` → push to Artifact Registry → `gcloud run jobs update` |

All workflows authenticate via Workload Identity Federation.

---

## Phase 2 Notes (out of scope, design implications)

- `activeNodeIds: string[]` prop on the graph component must be wired from Phase 1 (no-op until Phase 2)
- Stable node IDs in `graph.json` are a hard requirement — the Phase 2 agent cites nodes by ID
- FastAPI will gain a `/chat` endpoint backed by Claude with tool use (`search_knowledge_graph`, `get_now_playing`, `get_github_activity`, etc.)
- Redis (Cloud Memorystore) added for API response caching
- The agent's responses include cited `nodeIds`; the frontend highlights them in the graph in real time — grounding the response spatially
