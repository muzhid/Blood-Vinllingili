@echo off
echo Starting Blood-Villingili Bot...

if not exist .env (
    echo [ERROR] .env file is missing!
    pause
    exit /b
)

echo Starting API Server...
start "API Server" uvicorn api.index:app --reload --port 8000

echo Starting Telegram Bot...
start "Telegram Bot" python local_bot.py

echo.
echo All services started!
echo Frontend (if running): http://localhost:5173
echo.
pause
