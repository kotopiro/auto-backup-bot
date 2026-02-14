@echo off
title Auto Backup Bot Launcher
color 0A
echo.
echo ====================================
echo   Auto Backup Bot - Starting...
echo ====================================
echo.

REM Check .env file
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env
    pause
    exit /b 1
)

echo [OK] .env file found
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo [INFO] Starting Web Server...
start "Auto Backup Bot - Web Server" cmd /k python -m web.app
timeout /t 3 /nobreak > nul

echo [INFO] Starting Discord Bot...
start "Auto Backup Bot - Discord Bot" cmd /k python -m bot.main
timeout /t 2 /nobreak > nul

echo.
echo ====================================
echo   Both servers are now running!
echo ====================================
echo.
echo Web: http://localhost:5000
echo Bot: Check Discord
echo.
echo Press any key to exit...
pause > nul