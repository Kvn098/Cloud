@echo off
cd /d D:\DirectCreateApp

:: Start Python server with clear support
start "" python server.py

timeout /t 2 >nul

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 6" http://localhost:8080/apply_redirect.html
