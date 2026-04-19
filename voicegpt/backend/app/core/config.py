"""
Application Configuration — loads all settings from environment variables.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── OpenAI ───────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 512
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_STREAM: bool = True

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    POSTGRES_USER: str = "voicegpt"
    POSTGRES_PASSWORD: str = "voicegpt_secret"
    POSTGRES_DB: str = "voicegpt"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return "sqlite+aiosqlite:///./voicegpt.db"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return "sqlite:///./voicegpt.db"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_CONVERSATION_TTL: int = 86400  # 24 hours

    @property
    def REDIS_URL(self) -> str:
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-at-least-32-chars-long-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Whisper STT ───────────────────────────────────────────────────────────
    WHISPER_MODEL: str = "base"           # tiny | base | small | medium | large
    WHISPER_DEVICE: str = "cpu"           # cpu | cuda
    WHISPER_LANGUAGE: Optional[str] = None  # None = auto-detect

    # ── Coqui TTS ─────────────────────────────────────────────────────────────
    TTS_MODEL: str = "tts_models/en/ljspeech/tacotron2-DDC"
    TTS_VOCODER: Optional[str] = "vocoder_models/en/ljspeech/hifigan_v2"
    TTS_SPEAKER: Optional[str] = None
    TTS_LANGUAGE: str = "en"
    TTS_SAMPLE_RATE: int = 22050

    # ── FAISS Vector DB ───────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "data/faiss_index"
    FAISS_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    FAISS_TOP_K: int = 5

    # ── Workers / Celery ─────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Audio ─────────────────────────────────────────────────────────────────
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_CHUNK_SIZE: int = 4096          # bytes per WebSocket chunk
    VAD_SILENCE_THRESHOLD_MS: int = 800   # silence before end-of-speech

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
