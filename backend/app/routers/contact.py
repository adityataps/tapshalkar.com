import resend
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.config import settings

router = APIRouter()


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


@router.post("/contact")
async def contact(body: ContactRequest) -> dict:
    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": "site@tapshalkar.com",
        "to": "aditya@tapshalkar.com",
        "subject": f"Portfolio contact from {body.name}",
        "text": f"From: {body.name} <{body.email}>\n\n{body.message}",
    })
    return {"ok": True}
