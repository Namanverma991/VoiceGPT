# 🎙️ VoiceGPT — Production-Grade Real-Time Voice AI Agent

> A full-stack, low-latency Voice AI system: **Speak → Whisper STT → GPT LLM → Coqui TTS → Hear**

![Architecture](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20Whisper%20%7C%20Coqui-blueviolet)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🏗️ Architecture

```
Browser (React + WebSocket)
        │
        ▼  audio chunks (binary)
   [Nginx Proxy]
        │
        ▼  /ws/voice/{session_id}
   [FastAPI Backend]
        │
        ├─► [Whisper STT]    — audio → text
        ├─► [Redis Memory]   — conversation history
        ├─► [FAISS Vector]   — semantic long-term memory
        ├─► [GPT API]        — text → response (streaming)
        └─► [Coqui TTS]      — text → WAV audio chunks
                │
                ▼  base64 audio_chunk events
          Browser Audio API (playback)
```

---

## 📁 Project Structure

```
voicegpt/
├── frontend/          # React + Vite SPA
│   └── src/
│       ├── components/    # MicButton, ChatWindow, AudioPlayer, Loader
│       ├── hooks/         # useSocket (WebSocket + Audio queue)
│       ├── pages/         # Home, Login
│       ├── services/      # api.js (Axios), socket.js (WebSocket)
│       └── store/         # Zustand: authStore, voiceStore
│
├── backend/           # FastAPI Python backend
│   └── app/
│       ├── api/v1/        # routes_auth, routes_chat, routes_voice
│       ├── core/          # config, security, logging
│       ├── db/            # SQLAlchemy session + base
│       ├── models/        # User, ChatSession, ChatMessage (ORM)
│       ├── schemas/       # Pydantic DTOs
│       ├── services/
│       │   ├── orchestrator/  # pipeline.py + controller.py
│       │   ├── stt/           # whisper_engine.py
│       │   ├── llm/           # gpt_client.py
│       │   ├── tts/           # coqui_engine.py
│       │   └── memory/        # redis_client.py, vector_db.py
│       ├── websockets/    # voice_socket.py
│       └── workers/       # Celery tasks
│
├── database/          # SQL schema + Redis config
├── infra/             # Docker, Kubernetes, Nginx
├── scripts/           # setup.sh, run_local.sh, deploy.sh
└── tests/             # pytest test suite
```

---

## ⚙️ Tech Stack

| Layer       | Technology                              |
|-------------|------------------------------------------|
| Frontend    | React 18, Vite, Zustand, Framer Motion  |
| Backend     | FastAPI, Python 3.11, async/await        |
| WebSocket   | FastAPI WebSocket, WebAudio API          |
| STT         | OpenAI Whisper (local)                   |
| LLM         | OpenAI GPT-4o-mini (streaming)           |
| TTS         | Coqui TTS (local neural voice)           |
| Short-term  | Redis (conversation history)             |
| Long-term   | FAISS + SentenceTransformers              |
| Database    | PostgreSQL + SQLAlchemy async            |
| Workers     | Celery + Redis broker                    |
| Proxy       | Nginx                                    |
| Infra       | Docker Compose, Kubernetes               |

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker + Docker Compose

### 1. Clone & Setup
```bash
git clone <your-repo>
cd voicegpt
bash scripts/setup.sh
```

### 2. Configure Environment
```bash
# backend/.env
OPENAI_API_KEY=sk-your-key-here
JWT_SECRET_KEY=change-me-to-32-char-secret
POSTGRES_HOST=localhost    # or 'postgres' for Docker
REDIS_HOST=localhost       # or 'redis' for Docker
```

### 3. Start with Docker (recommended)
```bash
cd infra/docker
docker-compose up --build
```

Or run locally without Docker:
```bash
# Start Postgres + Redis (Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=voicegpt_secret -e POSTGRES_DB=voicegpt postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Start services
bash scripts/run_local.sh
```

### 4. Access
| Service      | URL                              |
|--------------|----------------------------------|
| Frontend     | http://localhost:5173            |
| API Docs     | http://localhost:8000/docs       |
| Flower       | http://localhost:5555            |

---

## 🔌 WebSocket Event Reference

### Client → Server Events

| Event Type     | Payload                     | Description                     |
|----------------|-----------------------------|---------------------------------|
| `start_stream` | `{type}`                    | Begin audio stream              |
| audio binary   | `ArrayBuffer`               | Raw audio chunk (WEBM/Opus)     |
| `stop_stream`  | `{type}`                    | End of utterance — trigger AI   |
| `text_message` | `{type, text, language}`    | Direct text input               |
| `interrupt`    | `{type}`                    | Stop AI response immediately    |
| `ping`         | `{type}`                    | Keepalive                       |
| `clear_context`| `{type}`                    | Wipe conversation memory        |

### Server → Client Events

| Event Type   | Payload                                    | Description                    |
|--------------|--------------------------------------------|--------------------------------|
| `connected`  | `{session_id, language, user_id}`          | Connection established         |
| `transcript` | `{text, language, confidence, latency_ms}` | STT result                     |
| `audio_chunk`| `{chunk_id, data: base64, format: "wav"}`  | TTS audio chunk                |
| `audio_done` | `{total_chunks, latency_ms}`               | TTS stream complete            |
| `interrupted`| `{was_active}`                             | AI speech stopped              |
| `error`      | `{error_code, message}`                    | Error event                    |
| `pong`       | `{type}`                                   | Keepalive response             |

### Connection URL
```
ws://localhost:8000/ws/voice/{session_id}?token={jwt_token}&language={en|hi|hinglish}
```

---

## 📡 REST API Reference

### Auth
| Method | Endpoint                  | Description         |
|--------|---------------------------|---------------------|
| POST   | `/api/v1/auth/register`  | Create user account |
| POST   | `/api/v1/auth/login`     | Get JWT tokens      |
| POST   | `/api/v1/auth/refresh`   | Refresh access token|
| GET    | `/api/v1/auth/me`        | Get user profile    |
| POST   | `/api/v1/auth/logout`    | Logout              |

### Chat
| Method | Endpoint                         | Description           |
|--------|----------------------------------|-----------------------|
| POST   | `/api/v1/chat/sessions`         | Create session        |
| GET    | `/api/v1/chat/sessions`         | List sessions         |
| GET    | `/api/v1/chat/sessions/{id}`    | Get session + history |
| DELETE | `/api/v1/chat/sessions/{id}`    | Delete session        |
| POST   | `/api/v1/chat/text`             | Text chat (blocking)  |
| POST   | `/api/v1/chat/stream`           | SSE streaming text    |

### Voice
| Method | Endpoint                     | Description              |
|--------|------------------------------|--------------------------|
| POST   | `/api/v1/voice/transcribe`  | Upload audio → text      |
| POST   | `/api/v1/voice/synthesize`  | Text → WAV audio         |
| POST   | `/api/v1/voice/synthesize/stream` | Streaming TTS      |
| GET    | `/api/v1/voice/status`      | Model status             |

Full interactive docs: **http://localhost:8000/docs**

---

## 🧪 Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
# With coverage:
pytest tests/ --cov=app --cov-report=html
```

---

## 🌐 Language Support

| Code       | Language         | STT | LLM | TTS |
|------------|------------------|-----|-----|-----|
| `en`       | English          | ✅  | ✅  | ✅  |
| `hi`       | Hindi            | ✅  | ✅  | ⚠️  |
| `hinglish` | Hinglish (mixed) | ✅  | ✅  | ✅  |

> ⚠️ TTS Hindi requires a Hindi-capable Coqui model. Default model is English.
> Set `TTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2` for multilingual support.

---

## 🔧 Advanced Configuration

### Use GPU (CUDA)
```env
WHISPER_DEVICE=cuda
```

### Use Larger Whisper Model (more accurate, slower)
```env
WHISPER_MODEL=small    # or medium, large-v3
```

### Multilingual TTS (XTTS v2)
```env
TTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2
TTS_VOCODER=
TTS_LANGUAGE=hi
TTS_SPEAKER=Claribel Dervla   # or any supported speaker
```

---

## ☁️ Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f infra/kubernetes/

# Check rollout
kubectl rollout status deployment/voicegpt-backend
kubectl rollout status deployment/voicegpt-frontend

# Scale backend
kubectl scale deployment voicegpt-backend --replicas=4
```

Update domain in `infra/kubernetes/ingress.yaml` → `host: voicegpt.yourdomain.com`

---

## 🔐 Security Notes

- All API routes require JWT Bearer token (except `/auth/register` and `/auth/login`)
- WebSocket authenticates via `?token=` query param
- Passwords hashed with bcrypt
- JWT with configurable expiry
- Rate limiting via Nginx (`30 req/s` API, `5 req/s` auth)
- In production: add token deny-listing in Redis on logout

---

## 📦 Logs

```bash
# Docker
docker-compose logs -f backend

# Local
tail -f logs/app.log
```

---

## 🙌 Credits

- [OpenAI Whisper](https://github.com/openai/whisper) — STT
- [Coqui TTS](https://github.com/coqui-ai/TTS) — Neural TTS
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [FAISS](https://faiss.ai/) — Vector similarity search
