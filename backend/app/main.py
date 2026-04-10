from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, graph, contact, currently

app = FastAPI(title="tapshalkar-backend", docs_url=None, redoc_url=None)

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
