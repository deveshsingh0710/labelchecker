@echo off
title LabelCheck - FastAPI Backend
echo Starting LabelCheck Backend (FastAPI + OpenCV + Tesseract OCR)...
cd /d "%~dp0\backend"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
pause
