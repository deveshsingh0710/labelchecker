@echo off
title Push LabelCheck to GitHub
echo ===================================================
echo Pushing LabelCheck to GitHub:
echo https://github.com/deveshsingh0710/labelcheck.git
echo ===================================================
echo.
cd /d "%~dp0"
git push -u origin main
echo.
pause
