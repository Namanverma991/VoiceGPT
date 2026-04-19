"""
GPT LLM Client — async OpenAI client with streaming, context management,
conversation history, and Hinglish system prompts.
"""

import time
import asyncio
from typing import AsyncIterator, List, Optional

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ─── System Prompts ───────────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "en": (
        "You are VoiceGPT, a friendly and knowledgeable AI voice assistant. "
        "Your words are being converted to speech in real-time, so keep responses concise (1-3 sentences max). "
        "Speak naturally, like a human talking. Since you ARE a voice assistant, never say you are a text-based model."
    ),
    "hi": (
        "Aap VoiceGPT hain — ek madadgaar AI voice assistant. "
        "Jawab seedha aur mukhtasar do (2-3 sentences). "
        "Hindi mein baat karo unless user English mein puchhe."
    ),
    "hinglish": (
        "You are VoiceGPT — an AI voice assistant who speaks in Hinglish. "
        "Mix Hindi and English naturally. Keep responses short and snappy. "
        "You are currently talking to the user via voice, so don't use complex formatting or markdown. "
        "Never say you cannot speak; you are a voice AI after all!"
    ),
}


class GPTClient:
    """
    Async GPT client with:
    - Streaming token generation
    - Conversation history (passed from Redis)
    - Context-aware system prompt
    - Token usage tracking
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
            organization=settings.OPENAI_ORG_ID or None,
            timeout=30.0,
            default_headers={
                "HTTP-Referer": "http://localhost:5173", # Optional for OpenRouter
                "X-Title": "VoiceGPT",
            } if settings.OPENAI_BASE_URL and "openrouter.ai" in settings.OPENAI_BASE_URL else None
        )

    def _build_messages(
        self,
        user_message: str,
        history: List[dict],
        language: str = "en",
    ) -> List[dict]:
        """Build OpenAI messages array from history + new user message."""
        system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"])
        messages = [{"role": "system", "content": system_prompt}]
        # Trim history to last N messages to stay within context window
        messages.extend(history[-20:])
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(
        self,
        user_message: str,
        history: Optional[List[dict]] = None,
        language: str = "en",
    ) -> dict:
        """
        Non-streaming chat completion.

        Returns:
            {"text": str, "tokens_used": int, "latency_ms": int}
        """
        start = time.monotonic()
        messages = self._build_messages(user_message, history or [], language)

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
            stream=False,
        )

        text = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else 0
        latency_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "LLM response",
            tokens=tokens,
            latency_ms=latency_ms,
            preview=text[:60],
        )

        return {"text": text, "tokens_used": tokens, "latency_ms": latency_ms}

    async def stream_chat(
        self,
        user_message: str,
        history: Optional[List[dict]] = None,
        language: str = "en",
    ) -> AsyncIterator[str]:
        """
        Streaming chat — yields tokens one by one.
        Yields: individual token strings
        Final yield: dict with metadata {"__meta__": True, "tokens_used": int}
        """
        messages = self._build_messages(user_message, history or [], language)
        token_count = 0

        # MOCK FOR MISSING API KEY
        if settings.OPENAI_API_KEY == "" or "your-openai" in settings.OPENAI_API_KEY:
            mock_response = "I am a VoiceGPT mock response. Please add your OpenAI API Key to the .env file to talk to the real AI!"
            for word in mock_response.split():
                yield word + " "
                await asyncio.sleep(0.05)
            logger.info("Mock LLM stream complete")
            return

        stream = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
            stream=True,
        )
        async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    token_count += 1
                    yield delta.content

        logger.info("LLM stream complete", tokens_approx=token_count)

    async def embed_text(self, text: str) -> List[float]:
        """Generate text embedding for FAISS semantic memory."""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding


# ─── Singleton ────────────────────────────────────────────────────────────────
gpt_client = GPTClient()
