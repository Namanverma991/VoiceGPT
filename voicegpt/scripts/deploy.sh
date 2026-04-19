#!/usr/bin/env bash
# ============================================================
# VoiceGPT — Docker Compose Deployment Script
# Usage: bash scripts/deploy.sh [local|production]
# ============================================================

set -e

TARGET=${1:-local}
info()  { echo -e "\033[0;32m[DEPLOY]\033[0m $*"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m  $*"; }

info "=== VoiceGPT Deployment: $TARGET ==="

if ! command -v docker &>/dev/null; then
  error "Docker required. Install from https://docs.docker.com/get-docker/"
  exit 1
fi

cd "$(dirname "$0")/../infra/docker"

if [ "$TARGET" = "local" ]; then
  info "Building and starting all services..."
  docker-compose pull postgres redis 2>/dev/null || true
  docker-compose up --build -d

  info ""
  info "✅  Stack is up!"
  info "   Frontend:    http://localhost:3000"
  info "   Backend API: http://localhost:8000"
  info "   API Docs:    http://localhost:8000/docs"
  info "   Flower:      http://localhost:5555"
  info ""
  info "Logs: docker-compose logs -f backend"
  info "Stop: docker-compose down"

elif [ "$TARGET" = "production" ]; then
  info "Production build..."
  docker-compose -f docker-compose.yml build

  info "Pushing images (set REGISTRY env var)..."
  REGISTRY=${REGISTRY:-your-registry.io/voicegpt}
  docker tag voicegpt-backend:latest "$REGISTRY/backend:latest"
  docker tag voicegpt-frontend:latest "$REGISTRY/frontend:latest"
  docker push "$REGISTRY/backend:latest"
  docker push "$REGISTRY/frontend:latest"

  info "Applying Kubernetes manifests..."
  kubectl apply -f ../kubernetes/
  kubectl rollout status deployment/voicegpt-backend
  kubectl rollout status deployment/voicegpt-frontend

  info "✅ Production deployment complete!"
else
  error "Unknown target: $TARGET. Use 'local' or 'production'."
  exit 1
fi
