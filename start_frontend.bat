@echo off
echo ========================================
echo Starting Frontend Server
echo ========================================
cd frontend

echo.
echo Frontend will run at: http://localhost:8080
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python -m http.server 8080

pause

