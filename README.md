# 🎙️ VoiceGPT: Production-Grade Real-Time Voice AI Agent

> **Experience the future of human-AI interaction.** VoiceGPT is a high-performance, low-latency system that enables seamless voice-to-voice conversations in real-time. 

![Aesthetics](https://img.shields.io/badge/Aesthetics-Premium-gold)
![Performance](https://img.shields.io/badge/Latency-Low-green)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20Whisper%20%7C%20Coqui-blueviolet)

---

## 🌟 Project Intro
**VoiceGPT** is not just another chatbot; it's a fully orchestrated Voice AI Agent designed for production environments. It bridges the gap between text-based LLMs and natural vocal communication. By combining state-of-the-art Speech-to-Text (STT), Large Language Models (LLM), and Text-to-Speech (TTS), it creates an " Jarvis-like" experience that is both responsive and intelligent.

## 📖 About the Project
This project was built to solve the challenges of high-latency voice systems. Most voice agents suffer from "turn-taking lag." VoiceGPT uses a **streaming-first architecture** and **WebSockets** to handle audio chunks in parallel, significantly reducing the perceived response time.

### Key Features:
- **Zero-Turn Lag**: Real-time audio streaming ensures responses begin as soon as the AI starts thinking.
- **Multilingual Support**: Switch between English, Hindi, and "Hinglish" seamlessly.
- **Memory-Augmented**: Integrated Redis for session memory and FAISS for long-term semantic knowledge.
- **Micro-Animation UI**: A sleek React frontend with Framer Motion for a premium user experience.

---

## ⚙️ Working Workflow
The system operates on an orchestrated pipeline designed for speed and reliability:

1.  **Capture**: The browser captures audio using the Web Audio API and streams it via **WebSockets**.
2.  **STT (Speech-to-Text)**: **OpenAI Whisper** processes incoming audio chunks into text tokens.
3.  **Brain (LLM)**: **GPT-4o-mini** analyzes the text and streams back its response in real-time.
4.  **TTS (Text-to-Speech)**: The response is instantly fed into the **Coqui TTS** engine.
5.  **Streaming Playback**: Audio is streamed back to the user in chunks, allowing playback to start before the full response is even generated.

---

## 📂 Project Structure
```text
.
├── voicegpt/                 # Main Application Directory
│   ├── frontend/             # React (Vite) Single Page Application
│   │   ├── src/              # UI Components, Hooks, and Stores
│   │   └── vite.config.js    # Build configuration
│   ├── backend/              # FastAPI Python Backend
│   │   ├── app/              # API routes, services, and logic
│   │   ├── core/             # Configuration and Security
│   │   └── websockets/       # Real-time communication handlers
│   ├── ai_models/            # Local model weights (Whisper/TTS)
│   ├── infra/                # DevOps: Docker, K8s, Nginx
│   ├── scripts/              # Automation: setup, run, and deploy
│   ├── database/             # Persistence layers (SQL & Redis)
│   └── README.md             # (Legacy/Internal) Documentation
├── .gitignore                # Global ignore rules (ignores venv, .env)
├── requirements.txt          # Python dependencies
└── README.md                 # Primary Documentation (You are here)
```

---

## 🚀 Quick Start
To get the system running locally:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   cd voicegpt/frontend && npm install
   ```
2. **Setup Environment**:
   Configure your `OPENAI_API_KEY` in `voicegpt/backend/app/core/config.py` or a `.env` file.
3. **Run the Application**:
   Use the provided batch script for a quick start:
   ```bash
   ./run.bat
   ```

## 🛠️ Tech Stack & Credits
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Async Python)
- **Frontend**: [React](https://reactjs.org/) + [Vite](https://vitejs.dev/) + [Zustand](https://github.com/pmndrs/zustand)
- **Voice Intelligence**: [OpenAI Whisper](https://github.com/openai/whisper) & [Coqui TTS](https://github.com/coqui-ai/TTS)
- **Orchestration**: [Docker](https://www.docker.com/) & [Nginx](https://www.nginx.com/)

---

## 📜 License
Licensed under the [MIT License](LICENSE).

Made with ❤️ by [Namanverma991](https://github.com/Namanverma991)
