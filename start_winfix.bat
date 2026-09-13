@echo off
setlocal

REM ============================================
REM WinFix Agent - One Click Launcher
REM ============================================

REM Get the directory where this BAT file lives
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

REM ============================================
REM Request Administrator privileges
REM ============================================

net session >nul 2>&1

if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...

    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM ============================================
REM Start WinFix Backend
REM ============================================

echo.
echo ============================================
echo Starting WinFix Agent...
echo ============================================
echo.

echo Starting backend on port 9000...

start "WinFix Backend" /min cmd /c ^
"cd /d "%BACKEND%" && ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 9000"

REM ============================================
REM Start Frontend
REM ============================================

echo Starting frontend...

start "WinFix Frontend" /min cmd /c ^
"cd /d "%FRONTEND%" && npm run dev"

REM ============================================
REM Wait for services
REM ============================================

echo.
echo Waiting for WinFix services to start...

timeout /t 5 /nobreak >nul

REM ============================================
REM Open WinFix in Edge App Mode
REM ============================================

echo Opening WinFix...

start "" msedge.exe --app=http://127.0.0.1:5173

echo.
echo ============================================
echo WinFix Agent launched successfully!
echo ============================================

endlocal
exit
