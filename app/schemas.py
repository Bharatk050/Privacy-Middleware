from typing import Literal

from pydantic import BaseModel, Field


class SessionCreated(BaseModel):
    session_id: str
    expires_in_seconds: int


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str = Field(min_length=1, max_length=100_000)


class ProtectedMessageResponse(BaseModel):
    session_id: str
    role: Literal["assistant"] = "assistant"
    content: str
    detected_entities: dict[str, int]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
