@echo off
setlocal

REM ============================================
REM WinFix Agent Launcher
REM ============================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

REM --------------------------------------------
REM Request Administrator privileges
REM --------------------------------------------

net session >nul 2>&1

if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================
echo Starting WinFix Agent
echo ============================================

REM --------------------------------------------
REM Start Backend
REM --------------------------------------------

echo Starting backend...

start "WinFix Backend" /min cmd /k "cd /d "%BACKEND%" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 9000"

REM Give backend a moment
timeout /t 2 /nobreak >nul

REM --------------------------------------------
REM Start Frontend
REM --------------------------------------------

echo Starting frontend...

start "WinFix Frontend" /min cmd /k "cd /d "%FRONTEND%" && npm run dev"

REM --------------------------------------------
REM Wait for frontend
REM --------------------------------------------

timeout /t 5 /nobreak >nul

REM --------------------------------------------
REM Open WinFix in Edge App Mode
REM --------------------------------------------

echo Opening WinFix...

start "" msedge.exe --app=http://127.0.0.1:5173

exit
