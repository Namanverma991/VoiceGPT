"""
Voice WebSocket Handler — /ws/voice/{session_id}
Real-time bidirectional audio streaming with interrupt support.

Event types (client → server):
    audio_chunk   : binary audio data (raw PCM/WEBM chunk)
    start_stream  : begin a new utterance
    stop_stream   : end of speech — trigger STT+LLM+TTS
    interrupt     : stop current AI speech immediately
    ping          : keepalive

Event types (server → client):
    connected       : session established
    transcript      : STT result text
    llm_token       : streaming LLM token
    audio_chunk     : TTS audio bytes (base64)
    audio_done      : TTS stream complete
    interrupted     : AI speech stopped
    error           : error event with code and message
    pong            : keepalive reply
"""

import asyncio
import base64
import json
import time
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.core.config import settings
from app.core.security import decode_token
from app.services.orchestrator.controller import session_controller
from app.services.orchestrator.pipeline import VoicePipeline
from app.services.memory.redis_client import get_memory

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── WebSocket Connection Manager ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws
        logger.info("WebSocket connected", session_id=session_id)

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)
        session_controller.cleanup_session(session_id)
        logger.info("WebSocket disconnected", session_id=session_id)

    async def send_json(self, session_id: str, data: dict):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception as e:
                logger.warning("Failed to send WS message", session_id=session_id, error=str(e))

    async def send_bytes(self, session_id: str, data: bytes):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_bytes(data)
            except Exception as e:
                logger.warning("Failed to send WS bytes", session_id=session_id, error=str(e))


manager = ConnectionManager()


# ─── WebSocket Route ──────────────────────────────────────────────────────────
@router.websocket("/ws/voice/{session_id}")
async def voice_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None, description="JWT access token"),
    language: str = Query("en", description="Conversation language"),
):
    """
    Real-time voice AI WebSocket endpoint.
    Authentication via ?token=<jwt> query param.
    """
    # ── Authenticate ──────────────────────────────────────────────────────────
    user_id: Optional[str] = None
    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
        except Exception:
            await websocket.close(code=4001)
            logger.warning("WS auth failed — invalid token", session_id=session_id)
            return

    # Accept
    await manager.connect(session_id, websocket)

    # Send connection acknowledgment
    await manager.send_json(session_id, {
        "type": "connected",
        "session_id": session_id,
        "language": language,
        "user_id": user_id,
        "message": "VoiceGPT WebSocket ready",
    })

    pipeline = session_controller.get_or_create_pipeline(session_id, language)
    audio_buffer = bytearray()
    is_streaming = False

    try:
        while True:
            try:
                # Receive next message (text JSON or binary audio)
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=120.0,  # 2-minute inactivity timeout
                )
            except asyncio.TimeoutError:
                await manager.send_json(session_id, {"type": "pong", "message": "idle timeout"})
                break

            # ── Binary audio chunk ────────────────────────────────────────────
            if "bytes" in message and message["bytes"]:
                if is_streaming:
                    audio_buffer.extend(message["bytes"])
                continue

            # ── Text/JSON event ───────────────────────────────────────────────
            if "text" not in message or not message["text"]:
                continue

            try:
                event = json.loads(message["text"])
            except json.JSONDecodeError:
                await manager.send_json(session_id, {
                    "type": "error",
                    "error_code": "INVALID_JSON",
                    "message": "Invalid JSON payload",
                })
                continue

            event_type = event.get("type", "")

            # ── start_stream ──────────────────────────────────────────────────
            if event_type == "start_stream":
                audio_buffer.clear()
                is_streaming = True
                logger.debug("Audio stream started", session_id=session_id)

            # ── stop_stream ───────────────────────────────────────────────────
            elif event_type == "stop_stream":
                is_streaming = False
                captured_audio = bytes(audio_buffer)
                audio_buffer.clear()

                if len(captured_audio) < 100:
                    await manager.send_json(session_id, {
                        "type": "error",
                        "error_code": "EMPTY_AUDIO",
                        "message": "No audio data received",
                    })
                    continue

                # Run the AI pipeline in background for non-blocking behavior
                task = asyncio.create_task(
                    _handle_voice_turn(
                        session_id=session_id,
                        audio_bytes=captured_audio,
                        pipeline=pipeline,
                        language=language,
                    )
                )
                session_controller.register_task(session_id, task)

            # ── text_message (text-only, no audio) ────────────────────────────
            elif event_type == "text_message":
                text = event.get("text", "").strip()
                lang = event.get("language", language)
                if not text:
                    continue

                task = asyncio.create_task(
                    _handle_text_turn(
                        session_id=session_id,
                        text=text,
                        pipeline=pipeline,
                        language=lang,
                    )
                )
                session_controller.register_task(session_id, task)

            # ── interrupt ─────────────────────────────────────────────────────
            elif event_type == "interrupt":
                was_active = await session_controller.interrupt(session_id)
                await manager.send_json(session_id, {
                    "type": "interrupted",
                    "was_active": was_active,
                })
                logger.info("Interrupt received", session_id=session_id, was_active=was_active)

            # ── ping ──────────────────────────────────────────────────────────
            elif event_type == "ping":
                await manager.send_json(session_id, {"type": "pong"})

            # ── clear_context ─────────────────────────────────────────────────
            elif event_type == "clear_context":
                memory = await get_memory()
                await memory.clear(session_id)
                await manager.send_json(session_id, {
                    "type": "context_cleared",
                    "session_id": session_id,
                })

            else:
                logger.debug("Unknown WS event type", event_type=event_type)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e), exc_info=True)
        try:
            await manager.send_json(session_id, {
                "type": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        manager.disconnect(session_id)


# ─── Voice Turn Handler ────────────────────────────────────────────────────────
async def _handle_voice_turn(
    session_id: str,
    audio_bytes: bytes,
    pipeline: VoicePipeline,
    language: str,
):
    """Process one voice utterance: STT → transcript event → streaming TTS audio."""
    t0 = time.monotonic()
    try:
        # STT
        stt_result = await pipeline._stt(audio_bytes, language)
        transcript = stt_result.get("text", "").strip()
        detected_lang = stt_result.get("language", language)

        if not transcript:
            await manager.send_json(session_id, {
                "type": "transcript",
                "text": "",
                "confidence": 0.0,
                "message": "No speech detected",
            })
            return

        # Emit transcript immediately
        await manager.send_json(session_id, {
            "type": "transcript",
            "text": transcript,
            "language": detected_lang,
            "confidence": round(stt_result.get("confidence", 0.0), 3),
            "latency_ms": int((time.monotonic() - t0) * 1000),
        })

        # Check interrupt after STT
        if await session_controller.check_interrupt(session_id):
            await manager.send_json(session_id, {"type": "interrupted"})
            return

        # Stream LLM + TTS audio chunks
        chunk_id = 0
        full_response = ""
        async for audio_chunk in pipeline.stream_voice_response(transcript, language=detected_lang):
            if await session_controller.check_interrupt(session_id):
                await manager.send_json(session_id, {"type": "interrupted"})
                return
            # Send audio as base64 JSON
            await manager.send_json(session_id, {
                "type": "audio_chunk",
                "chunk_id": chunk_id,
                "data": base64.b64encode(audio_chunk).decode("utf-8"),
                "format": "wav",
            })
            chunk_id += 1

        total_latency = int((time.monotonic() - t0) * 1000)
        await manager.send_json(session_id, {
            "type": "audio_done",
            "total_chunks": chunk_id,
            "latency_ms": total_latency,
        })

    except asyncio.CancelledError:
        logger.info("Voice turn cancelled (interrupt)", session_id=session_id)
        await manager.send_json(session_id, {"type": "interrupted"})
    except Exception as e:
        logger.error("Voice turn error", session_id=session_id, error=str(e), exc_info=True)
        await manager.send_json(session_id, {
            "type": "error",
            "error_code": "PIPELINE_ERROR",
            "message": str(e),
        })
    finally:
        session_controller.remove_task(session_id)


# ─── Text Turn Handler ─────────────────────────────────────────────────────────
async def _handle_text_turn(
    session_id: str,
    text: str,
    pipeline: VoicePipeline,
    language: str,
):
    """Handle text-only input: LLM streaming tokens → TTS audio."""
    try:
        chunk_id = 0
        async for audio_chunk in pipeline.stream_voice_response(text, language=language):
            if await session_controller.check_interrupt(session_id):
                await manager.send_json(session_id, {"type": "interrupted"})
                return
            await manager.send_json(session_id, {
                "type": "audio_chunk",
                "chunk_id": chunk_id,
                "data": base64.b64encode(audio_chunk).decode("utf-8"),
                "format": "wav",
            })
            chunk_id += 1

        # Get the LLM response text from memory for speechSynthesis fallback
        response_text = ""
        try:
            mem = await get_memory()
            history = await mem.get_history(session_id)
            for msg in reversed(history):
                if msg.get("role") == "assistant":
                    response_text = msg.get("content", "")
                    break
        except Exception:
            pass

        # Emit the response text as llm_token BEFORE audio_done so frontend can accumulate it
        if response_text:
            await manager.send_json(session_id, {
                "type": "llm_token",
                "token": response_text,
            })

        await manager.send_json(session_id, {
            "type": "audio_done",
            "total_chunks": chunk_id,
            "response_text": response_text,
        })

    except asyncio.CancelledError:
        await manager.send_json(session_id, {"type": "interrupted"})
    except Exception as e:
        logger.error("Text turn error", session_id=session_id, error=str(e))
        await manager.send_json(session_id, {
            "type": "error",
            "error_code": "TEXT_TURN_ERROR",
            "message": str(e),
        })
    finally:
        session_controller.remove_task(session_id)
