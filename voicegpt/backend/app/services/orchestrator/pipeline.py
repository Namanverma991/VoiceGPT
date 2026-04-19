"""
Orchestrator Pipeline — the core AI processing chain.
STT → Memory Retrieval → LLM → Memory Storage → TTS
"""

import asyncio
import re
import time
from typing import AsyncIterator, List, Optional

import structlog

from app.services.stt.whisper_engine import whisper_engine
from app.services.llm.gpt_client import gpt_client
from app.services.tts.coqui_engine import coqui_engine
from app.services.memory.redis_client import ConversationMemory, get_memory
from app.services.memory.vector_db import vector_memory

logger = structlog.get_logger(__name__)


class VoicePipeline:
    """
    Full end-to-end voice AI pipeline.

    Pipeline steps:
        1. [STT]     Audio bytes → text transcript
        2. [Memory]  Load Redis conversation history
        3. [Vector]  Retrieve relevant long-term memories
        4. [LLM]     Build context + call GPT
        5. [Memory]  Store exchange → Redis + FAISS
        6. [TTS]     Text response → audio bytes/stream
    """

    def __init__(self, session_id: str, language: str = "en"):
        self.session_id = session_id
        self.language = language

    # ─── Isolated STT (used by WebSocket) ─────────────────────────────────────
    async def _stt(self, audio_bytes: bytes, language: Optional[str] = None) -> dict:
        """Isolated STT step — used by WebSocket handler."""
        return await whisper_engine.transcribe_bytes(
            audio_bytes, language=language or self.language
        )

    # ─── Full Voice Round-Trip ────────────────────────────────────────────────
    async def process_audio(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> dict:
        """
        Process raw audio → returns:
        {
            "transcript": str,
            "response_text": str,
            "audio_bytes": bytes,  # WAV
            "latency_ms": int,
            "language": str,
        }
        """
        lang = language or self.language
        t0 = time.monotonic()

        # 1. STT
        stt_result = await self._stt(audio_bytes, lang)
        transcript = stt_result["text"]
        detected_lang = stt_result.get("language", lang)

        if not transcript.strip():
            return {
                "transcript": "",
                "response_text": "",
                "audio_bytes": b"",
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "language": detected_lang,
            }

        # 2. LLM
        llm_result = await self.process_text(transcript, language=detected_lang)

        # 3. TTS
        tts_bytes = await coqui_engine.synthesize(
            text=llm_result["text"],
            language=detected_lang,
        )

        total_latency = int((time.monotonic() - t0) * 1000)
        logger.info(
            "Voice pipeline complete",
            session_id=self.session_id,
            transcript_preview=transcript[:50],
            response_preview=llm_result["text"][:50],
            latency_ms=total_latency,
        )

        return {
            "transcript": transcript,
            "response_text": llm_result["text"],
            "audio_bytes": tts_bytes,
            "latency_ms": total_latency,
            "language": detected_lang,
        }

    # ─── Text-only (no STT, no TTS) ───────────────────────────────────────────
    async def process_text(self, text: str, language: Optional[str] = None) -> dict:
        """
        Text → LLM response (non-streaming).
        Returns: {"text": str, "tokens_used": int, "latency_ms": int}
        """
        lang = language or self.language
        t0 = time.monotonic()

        memory: ConversationMemory = await get_memory()
        history = await memory.get_history(self.session_id)

        # Enrich with semantic memory context
        vector_context = await vector_memory.get_relevant_context(text, self.session_id)
        if vector_context:
            history = [{"role": "system", "content": f"Relevant memory:\n{vector_context}"}] + history

        llm_result = await gpt_client.chat(
            user_message=text,
            history=history,
            language=lang,
        )
        response_text = llm_result["text"]

        # Update memory
        await memory.add_message(self.session_id, "user", text)
        await memory.add_message(self.session_id, "assistant", response_text)

        # Store in vector memory (non-blocking, best-effort)
        try:
            await vector_memory.add_memory(self.session_id, text, role="user")
            await vector_memory.add_memory(self.session_id, response_text, role="assistant")
        except Exception as e:
            logger.warning("Vector memory update failed", error=str(e))

        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "text": response_text,
            "tokens_used": llm_result.get("tokens_used", 0),
            "latency_ms": latency_ms,
        }

    # ─── Streaming LLM tokens ─────────────────────────────────────────────────
    async def stream_text(
        self, text: str, language: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream LLM response tokens.
        Persists exchange to memory after stream completes.
        """
        lang = language or self.language
        memory: ConversationMemory = await get_memory()
        history = await memory.get_history(self.session_id)

        vector_context = await vector_memory.get_relevant_context(text, self.session_id)
        if vector_context:
            history = [{"role": "system", "content": f"Relevant memory:\n{vector_context}"}] + history

        full_response = ""
        async for token in gpt_client.stream_chat(
            user_message=text, history=history, language=lang
        ):
            full_response += token
            yield token

        # Persist to memory after streaming finishes
        await memory.add_message(self.session_id, "user", text)
        await memory.add_message(self.session_id, "assistant", full_response)
        try:
            await vector_memory.add_memory(self.session_id, text, role="user")
            await vector_memory.add_memory(self.session_id, full_response, role="assistant")
        except Exception as e:
            logger.warning("Vector memory update failed", error=str(e))

    # ─── Streaming Voice Round-Trip ───────────────────────────────────────────
    async def stream_voice_response(
        self, transcript: str, language: str
    ) -> AsyncIterator[bytes]:
        """
        Stream TTS audio chunks sentence-by-sentence as LLM tokens arrive.
        Achieves lowest latency by synthesising each sentence as it's generated.
        """
        from app.core.config import settings

        sentence_buffer = ""

        async for token in self.stream_text(transcript, language=language):
            sentence_buffer += token
            # Flush on sentence boundary
            if re.search(r"[.!?।]\s*$", sentence_buffer.rstrip()):
                sentence = sentence_buffer.strip()
                sentence_buffer = ""
                if sentence:
                    try:
                        wav_bytes = await coqui_engine.synthesize(sentence, language=language)
                        for i in range(0, len(wav_bytes), settings.AUDIO_CHUNK_SIZE):
                            yield wav_bytes[i : i + settings.AUDIO_CHUNK_SIZE]
                    except Exception as e:
                        logger.error("TTS error during streaming", error=str(e))

        # Flush remaining text
        if sentence_buffer.strip():
            try:
                wav_bytes = await coqui_engine.synthesize(sentence_buffer.strip(), language=language)
                for i in range(0, len(wav_bytes), settings.AUDIO_CHUNK_SIZE):
                    yield wav_bytes[i : i + settings.AUDIO_CHUNK_SIZE]
            except Exception as e:
                logger.error("TTS flush error", error=str(e))
