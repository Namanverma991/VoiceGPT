"""
Orchestrator Controller — manages lifecycle of voice sessions,
interrupt handling, and pipeline dispatch.
"""

import asyncio
import uuid
from typing import Dict, Optional

import structlog

from app.services.orchestrator.pipeline import VoicePipeline
from app.services.memory.redis_client import get_memory

logger = structlog.get_logger(__name__)


class SessionController:
    """
    Manages active voice sessions and interrupt state.
    One controller is shared per process (singleton).
    """

    def __init__(self):
        # active_sessions: session_id → asyncio.Task
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._pipelines: Dict[str, VoicePipeline] = {}

    def get_or_create_pipeline(self, session_id: str, language: str = "en") -> VoicePipeline:
        if session_id not in self._pipelines:
            self._pipelines[session_id] = VoicePipeline(
                session_id=session_id, language=language
            )
        return self._pipelines[session_id]

    async def interrupt(self, session_id: str) -> bool:
        """
        Interrupt an in-progress AI response for a session.
        Cancels background task and signals via Redis.
        """
        memory = await get_memory()
        await memory.set_interrupt_flag(session_id)

        task = self._active_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.info("Session interrupted", session_id=session_id)
            return True
        return False

    def register_task(self, session_id: str, task: asyncio.Task) -> None:
        # Cancel previous task for this session if any
        old = self._active_tasks.get(session_id)
        if old and not old.done():
            old.cancel()
        self._active_tasks[session_id] = task

    def remove_task(self, session_id: str) -> None:
        self._active_tasks.pop(session_id, None)

    def cleanup_session(self, session_id: str) -> None:
        self._active_tasks.pop(session_id, None)
        self._pipelines.pop(session_id, None)
        logger.info("Session cleaned up", session_id=session_id)

    async def check_interrupt(self, session_id: str) -> bool:
        memory = await get_memory()
        return await memory.check_interrupt(session_id)


# ─── Singleton ────────────────────────────────────────────────────────────────
session_controller = SessionController()
