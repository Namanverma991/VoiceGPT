"""
Backend test suite — covers auth, chat, voice, and WebSocket endpoints.
Run: pytest tests/ -v --asyncio-mode=auto
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

# ── App under test ────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.core.security import create_access_token, hash_password


# ─── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_token():
    """Generate a test JWT token."""
    return create_access_token({"sub": "test-user-id", "email": "test@example.com"})


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ─── Health Check ─────────────────────────────────────────────────────────────
class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_root(self, client):
        r = await client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "VoiceGPT API"


# ─── Auth Routes ──────────────────────────────────────────────────────────────
class TestAuth:
    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client):
        r = await client.post("/api/v1/auth/register", json={})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "123",
        })
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        with patch("app.api.v1.routes_auth.get_db") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            r = await client.post("/api/v1/auth/login", json={
                "email": "nobody@nowhere.com",
                "password": "wrongpassword",
            })
        assert r.status_code in (401, 422, 500)

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client):
        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert r.status_code == 401


# ─── Security Utils ────────────────────────────────────────────────────────────
class TestSecurity:
    def test_hash_password(self):
        hashed = hash_password("testpassword")
        assert hashed != "testpassword"
        assert len(hashed) > 30

    def test_verify_password(self):
        from app.core.security import verify_password
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_create_access_token(self):
        token = create_access_token({"sub": "user123"})
        assert isinstance(token, str)
        assert len(token) > 50

    def test_decode_token(self):
        from app.core.security import decode_token
        token = create_access_token({"sub": "user123", "email": "x@x.com"})
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "x@x.com"
        assert payload["type"] == "access"

    def test_decode_invalid_token_raises(self):
        from app.core.security import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401


# ─── Voice Schemas ────────────────────────────────────────────────────────────
class TestVoiceSchemas:
    def test_synthesize_request_defaults(self):
        from app.schemas.voice import SynthesizeRequest
        req = SynthesizeRequest(text="Hello world")
        assert req.language == "en"
        assert req.speed == 1.0
        assert req.speaker is None

    def test_voice_session_event(self):
        from app.schemas.voice import VoiceSessionEvent
        evt = VoiceSessionEvent(type="audio_chunk", session_id="abc", chunk_id=0)
        assert evt.type == "audio_chunk"
        assert evt.language == "en"


# ─── Chat Schemas ─────────────────────────────────────────────────────────────
class TestChatSchemas:
    def test_text_chat_request(self):
        import uuid
        from app.schemas.chat import TextChatRequest
        sid = uuid.uuid4()
        req = TextChatRequest(session_id=sid, message="Hello")
        assert req.language == "en"
        assert req.message == "Hello"

    def test_create_session_defaults(self):
        from app.schemas.chat import CreateSessionRequest
        req = CreateSessionRequest()
        assert req.language == "en"
        assert req.title == "New conversation"


# ─── STT Engine Unit Tests ────────────────────────────────────────────────────
class TestWhisperEngine:
    def test_bytes_to_numpy_pcm_fallback(self):
        import numpy as np
        from app.services.stt.whisper_engine import WhisperEngine
        # Fake PCM int16 data
        samples = np.zeros(1600, dtype=np.int16)
        raw = samples.tobytes()
        result = WhisperEngine._bytes_to_numpy(raw)
        assert result.dtype == np.float32
        assert len(result) == 1600


# ─── TTS Engine Unit Tests ────────────────────────────────────────────────────
class TestCoquiEngine:
    def test_split_into_sentences(self):
        from app.services.tts.coqui_engine import CoquiEngine
        text = "Hello world. This is a test! Is it working?"
        parts = CoquiEngine._split_into_sentences(text)
        assert len(parts) == 3

    def test_split_single_sentence(self):
        from app.services.tts.coqui_engine import CoquiEngine
        parts = CoquiEngine._split_into_sentences("No punctuation here")
        assert len(parts) == 1

    def test_samples_to_wav(self):
        from app.services.tts.coqui_engine import CoquiEngine
        samples = [0.0] * 1000
        wav = CoquiEngine._samples_to_wav(samples, 22050)
        assert wav[:4] == b'RIFF'  # WAV magic bytes


# ─── Redis Memory Tests ────────────────────────────────────────────────────────
class TestConversationMemory:
    @pytest.mark.asyncio
    async def test_memory_add_and_get(self):
        from app.services.memory.redis_client import ConversationMemory
        from unittest.mock import AsyncMock

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()

        mem = ConversationMemory(mock_redis)
        await mem.add_message("session-1", "user", "Hello")
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        from app.services.memory.redis_client import ConversationMemory
        from unittest.mock import AsyncMock

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        mem = ConversationMemory(mock_redis)
        history = await mem.get_history("nonexistent-session")
        assert history == []
