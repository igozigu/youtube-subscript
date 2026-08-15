@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    echo Setting up Python environment...
    python -m venv backend\venv
    call backend\venv\Scripts\pip.exe install -r backend\requirements.txt
)

start "" "backend\venv\Scripts\pythonw.exe" gui_app.py
exit
