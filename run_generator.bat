@echo off
echo ==========================================
echo Running Portfolio Generator...
echo ==========================================

cd /d "%~dp0"
call venv\Scripts\activate.bat
python scripts\portfolio_generator.py

echo.
echo ==========================================
echo Done! Press any key to exit...
pause >nul
