import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app import core
from app.config import settings

router = APIRouter()


@router.get("/graph")
async def get_graph() -> JSONResponse:
    try:
        data = await core.gcs.fetch_object(settings.gcs_bucket, "graph.json")
    except Exception:
        raise HTTPException(status_code=502, detail="Graph data unavailable")

    return JSONResponse(
        content=json.loads(data),
        headers={"Cache-Control": "public, max-age=300"},
    )
