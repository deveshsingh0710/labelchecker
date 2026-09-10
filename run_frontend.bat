@echo off
title LabelCheck - React Frontend
echo Starting LabelCheck Frontend (Vite + React + Tailwind)...
cd /d "%~dp0\frontend"
call npm.cmd run dev
pause
