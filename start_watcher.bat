@echo off
echo ==========================================
echo Starting Portfolio Watcher...
echo ==========================================

cd /d "%~dp0"
call venv\Scripts\activate.bat
python scripts\watcher.py

echo.
pause
