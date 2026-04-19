"""
Pydantic schemas for Voice — transcription and synthesis.
"""

from typing import Optional

from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_seconds: float
    segments: list = []


class SynthesizeRequest(BaseModel):
    text: str
    language: str = "en"
    speaker: Optional[str] = None
    speed: float = 1.0


class SynthesizeResponse(BaseModel):
    audio_url: str
    duration_seconds: float
    format: str = "wav"


class VoiceSessionEvent(BaseModel):
    """WebSocket event schema."""
    type: str
    session_id: Optional[str] = None
    data: Optional[str] = None          # base64 audio
    text: Optional[str] = None
    language: Optional[str] = "en"
    chunk_id: Optional[int] = None
    confidence: Optional[float] = None
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
