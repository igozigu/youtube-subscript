@echo off
chcp 65001 > nul
cd /d "%~dp0"

if exist "backend\venv\Scripts\pythonw.exe" (
    start "" "backend\venv\Scripts\pythonw.exe" gui_app.py
    exit
)

echo ===================================================
echo   YouTube Transcript Extractor - Initial Setup
echo ===================================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Python is not installed.
        echo Please install Python 3.10+ from https://www.python.org/downloads/
        echo (Make sure to check 'Add python.exe to PATH' during installation)
        echo.
        pause
        exit /b 1
    )
    set PY_CMD=py
) else (
    set PY_CMD=python
)

echo [2/3] Creating virtual environment...
%PY_CMD% -m venv backend\venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [3/3] Installing dependencies...
backend\venv\Scripts\pip.exe install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Setup completed! Launching application...
start "" "backend\venv\Scripts\pythonw.exe" gui_app.py
exit
