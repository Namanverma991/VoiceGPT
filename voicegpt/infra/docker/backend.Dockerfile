# ── VoiceGPT Backend Dockerfile ───────────────────────────────────────────────
FROM python:3.11-slim as base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgomp1 \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencies layer (cache-friendly) ──
FROM base as deps
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Production layer ──
FROM deps as production
COPY . .

# Create required dirs
RUN mkdir -p logs data/faiss_index data/audio /app/ai_models

# Non-root user for security
RUN useradd -m -u 1000 voicegpt && chown -R voicegpt:voicegpt /app
USER voicegpt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools"]
