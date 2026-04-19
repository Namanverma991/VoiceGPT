"""
Chat Routes — /api/v1/chat
Handles: session management, text chat, history retrieval.
"""

import uuid
from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    CreateSessionRequest,
    SessionSchema,
    SessionDetailSchema,
    TextChatRequest,
    TextChatResponse,
    MessageSchema,
)
from app.services.orchestrator.pipeline import VoicePipeline

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Create Session ───────────────────────────────────────────────────────────
@router.post("/sessions", response_model=SessionSchema, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=uuid.UUID(user_id),
        title=payload.title,
        language=payload.language,
    )
    db.add(session)
    await db.flush()
    logger.info("Chat session created", session_id=str(session.id), user_id=user_id)
    # Attach message_count for schema
    session.message_count = 0
    return session


# ─── List Sessions ────────────────────────────────────────────────────────────
@router.get("/sessions", response_model=List[SessionSchema])
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """List all sessions for the authenticated user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == uuid.UUID(user_id))
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()

    # Attach message counts
    for s in sessions:
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id)
        )
        s.message_count = count_result.scalar() or 0

    return sessions


# ─── Get Session Detail ───────────────────────────────────────────────────────
@router.get("/sessions/{session_id}", response_model=SessionDetailSchema)
async def get_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a session with its full message history."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == uuid.UUID(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.message_count = len(session.messages)
    return session


# ─── Delete Session ───────────────────────────────────────────────────────────
@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == uuid.UUID(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await db.delete(session)
    logger.info("Session deleted", session_id=str(session_id))
    return None


# ─── Text Chat (non-streaming) ────────────────────────────────────────────────
@router.post("/text", response_model=TextChatResponse)
async def text_chat(
    payload: TextChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a text message and get a full AI response."""
    # Verify session ownership
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == payload.session_id,
            ChatSession.user_id == uuid.UUID(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    pipeline = VoicePipeline(session_id=str(payload.session_id))
    result_data = await pipeline.process_text(
        text=payload.message,
        language=payload.language or session.language,
    )

    # Persist messages
    user_msg = ChatMessage(
        session_id=payload.session_id,
        role="user",
        content=payload.message,
    )
    ai_msg = ChatMessage(
        session_id=payload.session_id,
        role="assistant",
        content=result_data["text"],
        tokens_used=result_data.get("tokens_used", 0),
        latency_ms=result_data.get("latency_ms", 0),
    )
    db.add(user_msg)
    db.add(ai_msg)
    await db.flush()

    return TextChatResponse(
        session_id=payload.session_id,
        user_message=MessageSchema.model_validate(user_msg),
        assistant_message=MessageSchema.model_validate(ai_msg),
        latency_ms=result_data.get("latency_ms", 0),
    )


# ─── Streaming Text Chat ──────────────────────────────────────────────────────
@router.post("/stream")
async def stream_chat(
    payload: TextChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream LLM response as Server-Sent Events (SSE).
    Client reads: 'data: <token>\n\n'
    """
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == payload.session_id,
            ChatSession.user_id == uuid.UUID(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    pipeline = VoicePipeline(session_id=str(payload.session_id))

    async def event_stream():
        full_response = ""
        async for token in pipeline.stream_text(
            text=payload.message,
            language=payload.language or session.language,
        ):
            full_response += token
            yield f"data: {token}\n\n"

        # Persist after stream
        user_msg = ChatMessage(
            session_id=payload.session_id,
            role="user",
            content=payload.message,
        )
        ai_msg = ChatMessage(
            session_id=payload.session_id,
            role="assistant",
            content=full_response,
        )
        db.add(user_msg)
        db.add(ai_msg)
        await db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
