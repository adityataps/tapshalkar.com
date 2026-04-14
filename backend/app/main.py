import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core import gcs
from app.core.limiter import limiter
from app.routers import health, graph, contact, currently, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load GCS data once at startup and store on app.state."""
    try:
        app.state.graph = json.loads(
            await gcs.fetch_object(settings.gcs_bucket, "graph.json")
        )
    except Exception:
        app.state.graph = {"nodes": [], "edges": []}

    try:
        app.state.bio = (
            await gcs.fetch_object(settings.gcs_bucket, "bio.md")
        ).decode()
    except Exception:
        app.state.bio = ""

    try:
        app.state.currently = json.loads(
            await gcs.fetch_object(settings.gcs_bucket, "currently.json")
        )
    except Exception:
        app.state.currently = {}

    yield


app = FastAPI(title="tapshalkar-backend", docs_url=None, redoc_url=None, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.allowed_origin_pattern,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(graph.router, prefix="/api")
app.include_router(contact.router, prefix="/api")
app.include_router(currently.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
