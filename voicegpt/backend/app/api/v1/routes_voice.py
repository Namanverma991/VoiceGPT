"""
Voice Routes — /api/v1/voice
Handles: audio upload → STT transcribe, TTS synthesize REST endpoints.
Real-time voice uses WebSocket (/ws/voice).
"""

import io
import time
import uuid
import base64
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from app.core.security import get_current_user_id
from app.schemas.voice import TranscribeResponse, SynthesizeRequest, SynthesizeResponse
from app.services.stt.whisper_engine import whisper_engine
from app.services.tts.coqui_engine import coqui_engine

logger = structlog.get_logger(__name__)
router = APIRouter()

# Maximum upload size: 25 MB
MAX_AUDIO_BYTES = 25 * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/flac",
    "audio/m4a",
    "application/octet-stream",
}


# ─── Transcribe Audio File ────────────────────────────────────────────────────
@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WAV/WEBM/MP3/OGG)"),
    language: Optional[str] = Form(None, description="Language code, e.g. 'en', 'hi'. Auto-detect if omitted."),
    user_id: str = Depends(get_current_user_id),
):
    """
    Upload an audio file and receive a text transcription.
    Supports WAV, WEBM, MP3, OGG, FLAC.
    """
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type: {file.content_type}",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file too large. Max {MAX_AUDIO_BYTES // 1024 // 1024} MB.",
        )
    if len(audio_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file appears to be empty or too short.",
        )

    logger.info(
        "Transcription request",
        user_id=user_id,
        filename=file.filename,
        size_kb=round(len(audio_bytes) / 1024, 1),
        language=language,
    )

    result = await whisper_engine.transcribe_bytes(audio_bytes, language=language)

    return TranscribeResponse(
        text=result["text"],
        language=result["language"],
        confidence=result["confidence"],
        duration_seconds=result["duration_seconds"],
        segments=result["segments"],
    )


# ─── Synthesize Text → Audio ──────────────────────────────────────────────────
@router.post("/synthesize")
async def synthesize_speech(
    payload: SynthesizeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Convert text to speech and return WAV audio bytes.
    Returns: audio/wav binary response.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty")

    if len(payload.text) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text too long — max 2000 characters for REST endpoint. Use WebSocket for long content.",
        )

    logger.info(
        "TTS request",
        user_id=user_id,
        text_len=len(payload.text),
        language=payload.language,
        speaker=payload.speaker,
    )

    wav_bytes = await coqui_engine.synthesize(
        text=payload.text,
        language=payload.language,
        speaker=payload.speaker,
        speed=payload.speed,
    )

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=voice_response.wav",
            "X-Audio-Size": str(len(wav_bytes)),
        },
    )


# ─── Streaming TTS ────────────────────────────────────────────────────────────
@router.post("/synthesize/stream")
async def stream_synthesize(
    payload: SynthesizeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Stream synthesized audio chunks as they're generated, sentence by sentence.
    Each chunk is raw WAV bytes. Great for long texts.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty")

    async def generate():
        async for chunk in coqui_engine.stream_synthesize(
            text=payload.text,
            language=payload.language,
            speaker=payload.speaker,
            speed=payload.speed,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="audio/wav",
        headers={"Cache-Control": "no-cache"},
    )


# ─── Health / Model Status ────────────────────────────────────────────────────
@router.get("/status")
async def voice_status(user_id: str = Depends(get_current_user_id)):
    """Return voice model status and configuration."""
    from app.core.config import settings

    return {
        "stt": {
            "engine": "whisper",
            "model": settings.WHISPER_MODEL,
            "device": settings.WHISPER_DEVICE,
        },
        "tts": {
            "engine": "coqui",
            "model": settings.TTS_MODEL,
            "language": settings.TTS_LANGUAGE,
        },
    }
