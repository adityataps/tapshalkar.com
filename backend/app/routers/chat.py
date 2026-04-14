from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.config import settings
from app.core.chat import run_chat_stream
from app.core.limiter import limiter

router = APIRouter()

MAX_MESSAGE_LENGTH = 500
MAX_HISTORY_TURNS = 20


class ChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("content")
    @classmethod
    def content_max_length(cls, v: str) -> str:
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message exceeds {MAX_MESSAGE_LENGTH} characters")
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v


class ChatRequest(BaseModel):
    messages: list[ChatMessage]

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("messages must not be empty")
        return v[-MAX_HISTORY_TURNS:]  # keep last N turns


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    messages = [m.model_dump() for m in body.messages]

    async def generate():
        async for chunk in run_chat_stream(
            messages=messages,
            graph=request.app.state.graph,
            bio=request.app.state.bio,
            currently=request.app.state.currently,
            model_armor_template=settings.model_armor_template,
            api_key=settings.anthropic_api_key,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
