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
