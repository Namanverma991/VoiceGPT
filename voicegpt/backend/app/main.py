"""
VoiceGPT FastAPI Backend — Main Application Entry Point
"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import init_db, close_db
from app.api.v1 import routes_auth, routes_chat, routes_voice
from app.websockets.voice_socket import router as ws_router

# ─── Logging ──────────────────────────────────────────────────────────────────
setup_logging()
logger = structlog.get_logger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VoiceGPT API starting up", env=settings.ENVIRONMENT)
    await init_db()
    yield
    logger.info("VoiceGPT API shutting down")
    await close_db()


# ─── App Instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="VoiceGPT API",
    description="Production-grade real-time Voice AI Agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    logger.info(
        "HTTP request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
    )
    return response


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(routes_auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(routes_chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(routes_voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(ws_router, tags=["websocket"])


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "1.0.0", "env": settings.ENVIRONMENT}


@app.get("/", tags=["system"])
async def root():
    return {
        "service": "VoiceGPT API",
        "docs": "/docs",
        "health": "/health",
    }


# ─── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", None)},
    )
