@echo off
rem Double-click to start the Pilgrim Pipeline dashboard on this computer.
cd /d "%~dp0"
title Pilgrim Pipeline dashboard - keep this window open
echo.
echo   Pilgrim Pipeline dashboard
echo   --------------------------
echo   Starting... your browser will open http://localhost:8000 in a few seconds.
echo   KEEP THIS WINDOW OPEN while you use the dashboard. Closing it stops the
echo   dashboard; jobs still in the queue are saved and continue next time.
echo.
set PY=python
where python >nul 2>nul || set PY=py -3
start "" /b cmd /c "ping -n 6 127.0.0.1 >nul & start http://localhost:8000"
%PY% -m uvicorn dashboard.main:app --port 8000
echo.
echo   The dashboard has stopped. If you did not close it yourself, read the
echo   message above (a common cause: it is already running in another window).
pause
