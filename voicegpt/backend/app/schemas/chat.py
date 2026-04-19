"""
Pydantic schemas for Chat — sessions and messages.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class MessageSchema(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    audio_path: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionSchema(BaseModel):
    id: uuid.UUID
    title: str
    language: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class SessionDetailSchema(SessionSchema):
    messages: List[MessageSchema] = []


class CreateSessionRequest(BaseModel):
    title: str = "New conversation"
    language: str = "en"


class TextChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str
    language: str = "en"


class TextChatResponse(BaseModel):
    session_id: uuid.UUID
    user_message: MessageSchema
    assistant_message: MessageSchema
    latency_ms: int
