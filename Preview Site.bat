@echo off
title CalcPantry preview
cd /d "%~dp0"
start "" http://localhost:8000
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" build.py --serve
pause
