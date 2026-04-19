"""
Whisper STT Engine — async wrapper around OpenAI Whisper for local inference.
Supports: chunk-based streaming, language detection, Hinglish.
"""

import asyncio
import io
import time
from pathlib import Path
from typing import AsyncIterator, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# Lazy-loaded to avoid import penalty at startup
_model = None
_model_lock = asyncio.Lock()


async def get_whisper_model():
    """Load (or return cached) Whisper model — thread-safe."""
    global _model
    if _model is not None:
        return _model
    logger.info("MOCK Whisper model loaded")
    _model = "mock_model"
    return _model


class WhisperEngine:
    """
    Production Whisper STT engine.
    - Transcribes raw audio bytes (WAV/WEBM/PCM)
    - Returns text + language + confidence + segments
    - Supports partial (streaming) transcription via VAD chunking
    """

    SUPPORTED_FORMATS = {".wav", ".webm", ".mp3", ".ogg", ".flac", ".m4a"}

    def __init__(self):
        from app.core.config import settings
        self.settings = settings

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> dict:
        """
        Transcribe audio bytes → text.

        Returns:
            {
                "text": str,
                "language": str,
                "confidence": float,
                "duration_seconds": float,
                "segments": list[dict],
            }
        """
        await asyncio.sleep(0.5) # Simulate transcription time
        logger.info("MOCK STT complete")
        return {
            "text": "Hello, I am using a mock voice because I am running locally without heavy dependencies.",
            "language": "en",
            "confidence": 1.0,
            "duration_seconds": 2.0,
            "segments": [{"start": 0.0, "end": 2.0, "text": "Hello, I am using a mock voice because I am running locally without heavy dependencies."}],
        }

    async def transcribe_file(self, file_path: str | Path, language: Optional[str] = None) -> dict:
        """Transcribe audio from file path."""
        with open(file_path, "rb") as f:
            return await self.transcribe_bytes(f.read(), language=language)

    async def stream_transcribe(
        self,
        chunk_iterator: AsyncIterator[bytes],
        language: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """
        Stream VAD-chunked audio → yield partial transcriptions.
        Each yielded dict has: {"type": "partial"|"final", "text": str}
        """
        buffer = bytearray()
        silence_threshold_bytes = (
            self.settings.AUDIO_SAMPLE_RATE
            * self.settings.AUDIO_CHANNELS
            * 2  # 16-bit = 2 bytes
            * self.settings.VAD_SILENCE_THRESHOLD_MS
            // 1000
        )

        async for chunk in chunk_iterator:
            buffer.extend(chunk)
            # Yield partial every ~1s of audio
            if len(buffer) >= self.settings.AUDIO_SAMPLE_RATE * 2:
                try:
                    partial = await self.transcribe_bytes(bytes(buffer), language=language)
                    yield {"type": "partial", **partial}
                except Exception as e:
                    logger.warning("Partial transcription failed", error=str(e))

        # Final transcription from full buffer
        if buffer:
            try:
                final = await self.transcribe_bytes(bytes(buffer), language=language)
                yield {"type": "final", **final}
            except Exception as e:
                logger.error("Final transcription failed", error=str(e))
                yield {"type": "error", "text": "", "language": "en", "confidence": 0.0}

    @staticmethod
    def _bytes_to_numpy(audio_bytes: bytes) -> np.ndarray:
        """Convert raw audio bytes to float32 numpy array for Whisper."""
        import soundfile as sf

        try:
            # Try soundfile first (handles WAV, FLAC, OGG)
            buf = io.BytesIO(audio_bytes)
            data, sr = sf.read(buf, dtype="float32", always_2d=False)
            # Resample to 16kHz if needed
            if sr != 16000:
                import librosa  # type: ignore
                data = librosa.resample(data, orig_sr=sr, target_sr=16000)
            return data
        except Exception:
            # Fallback: treat as raw PCM int16
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            return audio_int16.astype(np.float32) / 32768.0


# ─── Module-level singleton ───────────────────────────────────────────────────
whisper_engine = WhisperEngine()
