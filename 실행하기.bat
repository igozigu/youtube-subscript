@echo off
chcp 65001 > nul
title YouTube 대본 추출기

echo ===================================================
echo   📺 YouTube 채널/재생목록 대본 추출기 실행 중...
echo ===================================================

cd /d "%~dp0"

:: 1. 가상환경 확인 및 생성
if not exist "backend\venv\Scripts\python.exe" (
    echo [1/2] 최초 실행: Python 가상환경을 구성하고 있습니다...
    python -m venv backend\venv
    call backend\venv\Scripts\pip.exe install -r backend\requirements.txt
)

:: 2. 프로그램 실행 (GUI 팝업 창 기동)
echo [2/2] 프로그램을 실행합니다...
start "" "backend\venv\Scripts\pythonw.exe" gui_app.py

exit
