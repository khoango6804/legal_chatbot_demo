@echo off
echo ========================================
echo Starting Backend Server
echo ========================================
cd backend

echo.
echo Setting environment variables...
set MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
set MODEL_HF_SUBFOLDER=model
set HF_TOKEN=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
set PORT=8000
set HOST=0.0.0.0
set CORS_ORIGINS=http://localhost:8080
set DATABASE_URL=sqlite:///./feedback.db

echo.
echo Environment variables set:
echo   MODEL_HF_REPO=%MODEL_HF_REPO%
echo   MODEL_HF_SUBFOLDER=%MODEL_HF_SUBFOLDER%
echo   PORT=%PORT%
echo.
echo Starting server...
echo Backend will run at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python app.py

pause

