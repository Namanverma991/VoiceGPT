"""
Redis Client — async Redis wrapper for short-term conversation memory,
session state, rate limiting, and caching.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = structlog.get_logger(__name__)

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get (or create) the async Redis connection pool."""
    global _redis_client
    if _redis_client is None:
        import fakeredis.aioredis
        _redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        logger.info("FakeRedis connection created")
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class ConversationMemory:
    """
    Redis-backed short-term conversation memory.
    Stores the last N messages per session as a JSON list.
    Automatically expires after TTL.
    """

    MAX_MESSAGES = 50  # messages to keep per session
    KEY_PREFIX = "conv:"
    SESSION_KEY_PREFIX = "session:"

    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = settings.REDIS_CONVERSATION_TTL

    def _key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}{session_id}"

    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return conversation history as list of {role, content} dicts."""
        raw = await self.redis.get(self._key(session_id))
        if not raw:
            return []
        return json.loads(raw)

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message and trim to MAX_MESSAGES."""
        history = await self.get_history(session_id)
        history.append({"role": role, "content": content})
        # Keep only the last MAX_MESSAGES
        history = history[-self.MAX_MESSAGES :]
        await self.redis.setex(
            self._key(session_id),
            self.ttl,
            json.dumps(history, ensure_ascii=False),
        )

    async def clear(self, session_id: str) -> None:
        """Delete conversation from Redis."""
        await self.redis.delete(self._key(session_id))

    async def set_session_meta(self, session_id: str, meta: Dict[str, Any]) -> None:
        """Store session metadata (language, user prefs, etc.)."""
        key = f"{self.SESSION_KEY_PREFIX}{session_id}"
        await self.redis.setex(key, self.ttl, json.dumps(meta))

    async def get_session_meta(self, session_id: str) -> Optional[Dict[str, Any]]:
        key = f"{self.SESSION_KEY_PREFIX}{session_id}"
        raw = await self.redis.get(key)
        return json.loads(raw) if raw else None

    async def set_interrupt_flag(self, session_id: str) -> None:
        """Signal that user interrupted AI speech."""
        await self.redis.setex(f"interrupt:{session_id}", 10, "1")

    async def check_interrupt(self, session_id: str) -> bool:
        """Check and clear interrupt flag."""
        value = await self.redis.get(f"interrupt:{session_id}")
        if value:
            await self.redis.delete(f"interrupt:{session_id}")
            return True
        return False

    async def increment_rate(self, key: str, window_seconds: int = 60) -> int:
        """Simple rate limiter — returns current count."""
        pipe = self.redis.pipeline()
        pipe.incr(f"rate:{key}")
        pipe.expire(f"rate:{key}", window_seconds)
        results = await pipe.execute()
        return results[0]


async def get_memory() -> ConversationMemory:
    """Dependency-injectable memory instance."""
    redis = await get_redis()
    return ConversationMemory(redis)
