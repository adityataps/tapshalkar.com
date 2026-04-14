# tapshalkar.com

Personal portfolio site. Monorepo containing frontend, backend, scheduled jobs, and infrastructure.

## Architecture

```
frontend/        # Next.js (App Router, static export) → GCS + Cloud CDN
backend/         # FastAPI, Python 3.13 → Cloud Run (scales to zero)
jobs/graph-gen/  # Cloud Run Job — fetches live data, calls Claude, writes graph.json to GCS
infra/           # Terraform — GCP: GCS, CDN, Cloud Run, Scheduler, IAM, Artifact Registry
.github/workflows/
```

**Frontend** is fully static — `next build` exports to a GCS bucket behind Cloud CDN. No Node server at runtime.

**Backend** serves the knowledge graph and handles chat via a `/chat` SSE endpoint backed by Claude with tool use. Deployed to Cloud Run (scales to zero between requests).

**Graph job** runs weekly via Cloud Scheduler. It fetches data from GitHub, Spotify, Steam, Trakt, and Apple Health, then calls Claude to synthesize a typed knowledge graph (`graph.json`) which is written to GCS and served via the backend.

**Chat agent** ("digital me") uses the knowledge graph as its primary knowledge base. It streams responses token-by-token and returns node IDs that get highlighted on the graph.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, `react-force-graph-2d` |
| Backend | FastAPI, Python 3.13, `uv`, Anthropic SDK |
| Graph job | Python 3.13, `uv`, Anthropic SDK |
| Infra | Terraform, GCP (Cloud Run, GCS, Cloud CDN, Cloud Scheduler, Secret Manager) |
| CI/CD | GitHub Actions + Workload Identity Federation |
| LLM | Claude (Anthropic) — graph synthesis + chat agent |

## Local Development

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend
cd backend && uv run uvicorn app.main:app --reload

# Graph job (one-off local run)
cd jobs/graph-gen && uv run python main.py
```

The backend requires a `.env` file with secrets (see `backend/app/config.py`). The graph job requires API keys for all data sources.

## Deployment

All deploys are triggered via GitHub Actions:

| Workflow | Trigger |
|---|---|
| `deploy-frontend.yml` | Push to `main` touching `frontend/` |
| `deploy-backend.yml` | Push to `main` touching `backend/` |
| `deploy-job.yml` | Push to `main` touching `jobs/graph-gen/` |

Infrastructure is managed with Terraform (`infra/`). Secrets are stored in Google Secret Manager and injected as environment variables at Cloud Run runtime — never in images or code.
