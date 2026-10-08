@echo off
rem Weekly calculator update check (Windows Task Scheduler runs this every Monday).
rem Writes update-report.md; opens it only when a source changed or a review is due.
title CalcPantry update check
cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" check_updates.py > update-check.log 2>&1
if errorlevel 1 start "" notepad "%~dp0update-report.md"
