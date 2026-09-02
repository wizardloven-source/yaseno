@echo off
chcp 65001 >nul
title YAseen ERP

echo ==========================================
echo   Starting YAseen ERP...
echo ==========================================

set "SERVER_BAT=C:\Users\MTC\Desktop\yaseeno\start_server.bat"

REM Check if server already running (via health endpoint or port)
netstat -an | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Backend already running on port 8000
    goto RUN_APP
)

echo Starting backend server...
cd /d C:\Users\MTC\Desktop\yaseeno

REM Launch server detached (uses its own window to avoid being tied to this script)
start "YAseen ERP Backend" /MIN cmd /c call "%SERVER_BAT%"

echo Waiting for server to initialize...
set /a attempts=0
:WAITLOOP
set /a attempts+=1
timeout /t 5 /nobreak >nul
netstat -an | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Backend started successfully!
    goto RUN_APP
)
if %attempts% LSS 10 goto WAITLOOP

echo ERROR: Backend failed to start after %attempts% attempts.
echo Please check that Python and dependencies are installed correctly.
echo Try running start_server.bat manually to see any error output.
pause
exit /b 1

:RUN_APP
echo.
echo Starting desktop application...
cd /d C:\Users\MTC\Desktop\yaseeno\frontend\build\windows\x64\runner\Release
start "" "ya_seen_erp_flutter.exe"

echo.
echo Done! The app should open now.
