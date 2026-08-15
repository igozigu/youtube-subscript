@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: 1. 가상환경이 정상 구축되어 있으면 즉시 실행
if exist "backend\venv\Scripts\pythonw.exe" (
    start "" "backend\venv\Scripts\pythonw.exe" gui_app.py
    exit
)

:: 2. 최초 1회 실행: 터미널에 친절한 진행 상태 출력
echo ===================================================
echo   📺 YouTube 대본 추출기 - 최초 1회 환경 설정
echo ===================================================
echo.

echo [1/3] Python 설치 확인 중...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [오류] Python이 설치되어 있지 않습니다.
        echo https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치해주세요.
        echo (※ 설치 시 'Add python.exe to PATH' 체크박스를 꼭 선택해주세요!)
        echo.
        pause
        exit /b 1
    )
    set PY_CMD=py
) else (
    set PY_CMD=python
)

echo [2/3] Python 가상환경(venv) 생성 중...
%PY_CMD% -m venv backend\venv
if %errorlevel% neq 0 (
    echo [오류] 가상환경 생성에 실패했습니다. Python 버전을 확인해주세요.
    pause
    exit /b 1
)

echo [3/3] 필요한 라이브러리 설치 중 (약 10~30초 소요)...
backend\venv\Scripts\pip.exe install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [오류] 라이브러리 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo   설정 완료! 프로그램을 실행합니다...
echo ===================================================
start "" "backend\venv\Scripts\pythonw.exe" gui_app.py
exit
