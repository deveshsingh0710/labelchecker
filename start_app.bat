@echo off
title LabelCheck - Launcher
echo Starting LabelCheck Full-Stack Application...
echo.

start "LabelCheck Backend" cmd /k "cd /d %~dp0\backend && python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul

start "LabelCheck Frontend" cmd /k "cd /d %~dp0\frontend && npm.cmd run dev"
timeout /t 2 /nobreak >nul

echo Opening browser at http://localhost:5173 ...
start http://localhost:5173
