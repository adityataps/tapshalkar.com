import asyncio
import resend
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.config import settings

router = APIRouter()
resend.api_key = settings.resend_api_key  # set once at import time


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


@router.post("/contact")
async def contact(body: ContactRequest) -> dict:
    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": "site@tapshalkar.com",
                "to": "aditya@tapshalkar.com",
                "subject": f"Portfolio contact from {body.name}",
                "text": f"From: {body.name} <{body.email}>\n\n{body.message}",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to send message") from exc
    return {"ok": True}
