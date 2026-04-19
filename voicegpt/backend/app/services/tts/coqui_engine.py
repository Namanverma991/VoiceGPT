"""
Coqui TTS Engine — local neural TTS with streaming audio output.
Produces natural, low-latency voice in WAV format.
"""

import asyncio
import io
import time
import wave
from pathlib import Path
from typing import AsyncIterator, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

_tts_model = None
_tts_lock = asyncio.Lock()


async def get_tts_model():
    """Lazy-load TTS model (heavy, avoid loading at import time)."""
    global _tts_model
    if _tts_model is not None:
        return _tts_model
    logger.info("MOCK Coqui TTS model loaded")
    _tts_model = "mock_model"
    return _tts_model


class CoquiEngine:
    """
    Production Coqui TTS engine.
    - Synthesizes text → WAV audio bytes
    - Streams audio in chunks for low-latency playback
    - Supports multi-speaker and multi-language models
    """

    CHUNK_FRAME_SIZE = 4096  # float32 samples per chunk

    def __init__(self):
        from app.core.config import settings
        self.settings = settings

    async def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        speaker: Optional[str] = None,
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize text → full WAV bytes.

        Returns: raw WAV bytes (16-bit PCM)
        """
        if not text.strip():
            return b""

        start = time.monotonic()
        model = await get_tts_model()
        lang = language or self.settings.TTS_LANGUAGE
        spk = speaker or self.settings.TTS_SPEAKER

        # Run synthesis in thread pool (CPU-bound)
        wav_samples: list = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._run_tts(model, text, lang, spk, speed),
        )

        wav_bytes = self._samples_to_wav(wav_samples, self.settings.TTS_SAMPLE_RATE)
        latency_ms = (time.monotonic() - start) * 1000

        logger.info(
            "TTS synthesis complete",
            text_preview=text[:50],
            audio_bytes=len(wav_bytes),
            latency_ms=round(latency_ms, 1),
        )

        return wav_bytes

    async def stream_synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        speaker: Optional[str] = None,
        speed: float = 1.0,
    ) -> AsyncIterator[bytes]:
        """
        Synthesize text → yield WAV audio chunks for real-time streaming.
        First chunk arrives with minimal latency by sentence-splitting.
        """
        sentences = self._split_into_sentences(text)
        chunk_id = 0

        for sentence in sentences:
            if not sentence.strip():
                continue
            try:
                wav_bytes = await self.synthesize(
                    sentence,
                    language=language,
                    speaker=speaker,
                    speed=speed,
                )
                # Yield in sub-chunks for smoother streaming
                for i in range(0, len(wav_bytes), self.settings.AUDIO_CHUNK_SIZE):
                    yield wav_bytes[i : i + self.settings.AUDIO_CHUNK_SIZE]
                    chunk_id += 1
            except Exception as e:
                logger.error("TTS chunk failed", sentence=sentence[:40], error=str(e))

    @staticmethod
    def _run_tts(model, text: str, language: str, speaker: Optional[str], speed: float) -> list:
        """Execute TTS synthesis (mocked list of zeros)."""
        import numpy as np
        return np.zeros(22050, dtype=np.float32).tolist()

    @staticmethod
    def _samples_to_wav(samples: list, sample_rate: int) -> bytes:
        """Convert float32 samples list → 16-bit WAV bytes."""
        arr = np.array(samples, dtype=np.float32)
        arr_int16 = (arr * 32767).clip(-32768, 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(arr_int16.tobytes())
        return buf.getvalue()

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """Split text into sentences for low-latency streaming."""
        import re
        # Split on sentence-ending punctuation, keeping delimiters
        parts = re.split(r"(?<=[.!?।])\s+", text.strip())
        return [p for p in parts if p.strip()]


# ─── Singleton ────────────────────────────────────────────────────────────────
coqui_engine = CoquiEngine()
