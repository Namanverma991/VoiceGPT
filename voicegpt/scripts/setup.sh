#!/usr/bin/env bash
# ============================================================
# VoiceGPT — Local Setup Script
# Run once to configure the environment.
# Usage: bash scripts/setup.sh
# ============================================================

set -e
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${COLOR_GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${COLOR_YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${COLOR_RED}[ERROR]${NC} $*"; }

info "=== VoiceGPT Local Setup ==="

# ── Check Python ──────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  error "Python 3.11+ required. Install from https://python.org"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python: $PYTHON_VERSION"

# ── Check Node ────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  error "Node.js 20+ required. Install from https://nodejs.org"
  exit 1
fi
info "Node: $(node -v)"

# ── Check Docker ──────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  warn "Docker not found. You'll need Docker for the full stack."
fi

# ── Create virtualenv ─────────────────────────────────────
info "Creating Python virtual environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate

# ── Install backend deps ──────────────────────────────────
info "Installing backend dependencies (this may take 5-10 minutes)..."
pip install --upgrade pip wheel setuptools -q
pip install -r requirements.txt

# ── Copy .env ─────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env 2>/dev/null || true
  warn "Created backend/.env — please add your OPENAI_API_KEY"
fi

cd ..

# ── Install frontend deps ─────────────────────────────────
info "Installing frontend dependencies..."
cd frontend
npm install --silent
cd ..

# ── Create required dirs ──────────────────────────────────
mkdir -p backend/data/faiss_index backend/data/audio logs ai_models/whisper ai_models/tts

# ── Pre-download Whisper model ────────────────────────────
info "Pre-downloading Whisper 'base' model (~140MB)..."
python3 -c "import whisper; whisper.load_model('base')" || warn "Whisper download failed — will retry on first run"

info ""
info "✅ Setup complete!"
info ""
info "Next steps:"
info "  1. Edit backend/.env and set OPENAI_API_KEY"
info "  2. Start services: bash scripts/run_local.sh"
info "  3. Open browser: http://localhost:5173"
