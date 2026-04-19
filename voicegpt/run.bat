@echo off
echo ==========================================
echo Starting VoiceGPT...
echo ==========================================

:: Start the Python Backend in a new command window
echo Launching Backend (FastAPI)...
start "VoiceGPT Backend" cmd /k "echo Starting Backend... && cd backend && .\.venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Start the Vite Frontend in a new command window
echo Launching Frontend (React)...
start "VoiceGPT Frontend" cmd /k "echo Starting Frontend... && cd frontend && npm run dev"

echo.
echo Both services are starting up!
echo Frontend URL: http://localhost:5173
echo Backend API Docs: http://localhost:8000/docs
echo.
echo IMPORTANT: To close the application, remember to close both command windows.
pause
