@echo off
setlocal enabledelayedexpansion

REM === 경로 설정 ===
set "BASE=C:\Users\315\backend1"
set "DASH=%BASE%\python_dashboard_starter"
set "VENV=%BASE%\.venv\Scripts"

REM === 1) FastAPI 먼저 (포트 8000) ===
start "FastAPI Server" cmd /k ^
  "cd /d %BASE% && call "%VENV%\activate" && uvicorn realtime_server:app --host 127.0.0.1 --port 8000 --reload"

REM 서버가 올라올 시간 줌
timeout /t 4 >nul

REM === 2) YOLO 송신기 (m.py) ===
start "YOLO Sender" cmd /k ^
  "cd /d %BASE% && call "%VENV%\activate" && python m.py"

REM YOLO가 전송 시작할 시간 살짝 줌
timeout /t 2 >nul

REM === 3) Streamlit 대시보드 (반드시 dashboard 폴더에서 실행) ===
start "Streamlit Dashboard" cmd /k ^
  "cd /d %DASH% && call "%VENV%\activate" && streamlit run app.py --server.port 8501 --server.headless true"

echo 🚀 All services started (FastAPI + YOLO + Streamlit)
exit /b
