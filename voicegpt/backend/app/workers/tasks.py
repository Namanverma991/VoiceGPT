"""
Celery Background Workers — heavy/async tasks offloaded from the request cycle.
Tasks: audio pre-processing, batch TTS, conversation summarization, cleanup.
"""

from celery import Celery
from celery.utils.log import get_task_logger

from app.core.config import settings

logger = get_task_logger(__name__)

# ─── Celery App ───────────────────────────────────────────────────────────────
celery_app = Celery(
    "voicegpt_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,    # Fair task distribution
    task_acks_late=True,             # Re-queue on worker crash
    task_reject_on_worker_lost=True,
    result_expires=3600,             # Results expire in 1 hour
)


# ─── Task: Pre-warm AI Models ─────────────────────────────────────────────────
@celery_app.task(name="tasks.prewarm_models", bind=True, max_retries=2)
def prewarm_models(self):
    """
    Pre-load Whisper + Coqui models into memory on worker startup.
    Reduces first-request latency significantly.
    """
    import asyncio

    async def _prewarm():
        from app.services.stt.whisper_engine import get_whisper_model
        from app.services.tts.coqui_engine import get_tts_model

        logger.info("Pre-warming Whisper model...")
        await get_whisper_model()
        logger.info("Pre-warming Coqui TTS model...")
        await get_tts_model()
        logger.info("Model pre-warm complete")

    try:
        asyncio.run(_prewarm())
        return {"status": "ok"}
    except Exception as exc:
        logger.error(f"Pre-warm failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


# ─── Task: Summarize Conversation ─────────────────────────────────────────────
@celery_app.task(name="tasks.summarize_conversation", bind=True, max_retries=3)
def summarize_conversation(self, session_id: str):
    """
    Summarize a conversation session using GPT and store it as a memory entry.
    Run periodically or when a session exceeds a message threshold.
    """
    import asyncio

    async def _summarize():
        from app.services.memory.redis_client import get_memory
        from app.services.llm.gpt_client import gpt_client
        from app.services.memory.vector_db import vector_memory

        memory = await get_memory()
        history = await memory.get_history(session_id)

        if len(history) < 6:
            return {"status": "skipped", "reason": "too_short"}

        history_text = "\n".join(
            f"{m['role'].title()}: {m['content']}" for m in history[-20:]
        )
        summary_result = await gpt_client.chat(
            user_message=f"Summarize this conversation in 3 sentences:\n\n{history_text}",
            history=[],
            language="en",
        )
        summary = summary_result["text"]

        await vector_memory.add_memory(session_id, f"[Summary] {summary}", role="system")
        logger.info(f"Conversation summarized for session {session_id}")
        return {"status": "ok", "summary": summary}

    try:
        result = asyncio.run(_summarize())
        return result
    except Exception as exc:
        logger.error(f"Summarization failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


# ─── Task: Batch TTS Pre-render ───────────────────────────────────────────────
@celery_app.task(name="tasks.batch_tts", bind=True, max_retries=2)
def batch_tts(self, texts: list, language: str = "en", output_dir: str = "/tmp/tts_cache"):
    """
    Pre-render a batch of texts to cached WAV files.
    Useful for common greetings/responses.
    """
    import asyncio
    import os

    async def _render():
        from app.services.tts.coqui_engine import coqui_engine
        os.makedirs(output_dir, exist_ok=True)
        results = []
        for i, text in enumerate(texts):
            try:
                wav = await coqui_engine.synthesize(text, language=language)
                path = os.path.join(output_dir, f"cache_{i}.wav")
                with open(path, "wb") as f:
                    f.write(wav)
                results.append({"text": text, "path": path, "status": "ok"})
            except Exception as e:
                results.append({"text": text, "error": str(e), "status": "error"})
        return results

    try:
        return asyncio.run(_render())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


# ─── Task: Cleanup Expired Sessions ──────────────────────────────────────────
@celery_app.task(name="tasks.cleanup_expired_audio")
def cleanup_expired_audio(max_age_hours: int = 24):
    """
    Remove TTS audio files older than max_age_hours from disk.
    Schedule via Celery beat.
    """
    import os
    import time
    from pathlib import Path

    audio_dir = Path("data/audio")
    if not audio_dir.exists():
        return {"cleaned": 0}

    cutoff = time.time() - (max_age_hours * 3600)
    cleaned = 0
    for f in audio_dir.glob("*.wav"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            cleaned += 1

    logger.info(f"Cleaned {cleaned} expired audio files")
    return {"cleaned": cleaned}


# ─── Celery Beat Schedule ─────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "cleanup-audio-daily": {
        "task": "tasks.cleanup_expired_audio",
        "schedule": 86400,  # every 24h
        "args": (24,),
    },
}
