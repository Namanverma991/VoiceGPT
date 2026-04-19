#!/usr/bin/env bash
# ============================================================
# VoiceGPT — Run All Services Locally (no Docker)
# Usage: bash scripts/run_local.sh
# ============================================================

set -e

BACKEND_PORT=8000
FRONTEND_PORT=5173

info() { echo -e "\033[0;32m[INFO]\033[0m  $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m  $*"; }

info "=== Starting VoiceGPT Local Stack ==="

# Check PostgreSQL + Redis (assumes running locally or via Docker)
info "Make sure PostgreSQL and Redis are running."
info "Quick start: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=voicegpt_secret postgres:16-alpine"
info "             docker run -d -p 6379:6379 redis:7-alpine"

# Kill any lingering processes
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# ── Backend ───────────────────────────────────────────────
info "Starting FastAPI backend on port $BACKEND_PORT..."
cd backend
source .venv/bin/activate 2>/dev/null || true
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port $BACKEND_PORT \
  --reload \
  --log-level info &
BACKEND_PID=$!
cd ..

# ── Frontend ──────────────────────────────────────────────
info "Starting Vite frontend on port $FRONTEND_PORT..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

info ""
info "✅  Services running!"
info "   Backend API: http://localhost:$BACKEND_PORT"
info "   API Docs:    http://localhost:$BACKEND_PORT/docs"
info "   Frontend:    http://localhost:$FRONTEND_PORT"
info ""
info "Press Ctrl+C to stop all services."

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; info 'Services stopped.'" EXIT
wait
