@echo off
setlocal enabledelayedexpansion

REM ===================================================
REM ✅ [인코딩 수정] 한글 깨짐 방지를 위해 CMD 인코딩을 UTF-8로 설정
chcp 65001 > nul
REM ===================================================

REM ==========================================
REM [경로 설정] 최종 확인 완료: C:\Users\315\Desktop\backend1
REM ==========================================
set "BASE=C:\Users\315\Desktop\backend1"
set "DASH=%BASE%\python_dashboard_starter"

REM 가상환경 이름 (사용자 확인: venv)
set "VENV=%BASE%\venv\Scripts"

REM ==========================================
REM [실행] 프로그램 가동
REM ==========================================

echo 1. FastAPI 서버 시작 중...
start "FastAPI Server" cmd /k "cd /d "%BASE%" && call "%VENV%\activate" && uvicorn realtime_server:app --host 127.0.0.1 --port 8000 --reload"

REM 서버 안정화 대기
timeout /t 4 >nul

echo 2. YOLO 송신기 시작 중...
start "YOLO Sender" cmd /k "cd /d "%BASE%" && call "%VENV%\activate" && python m.py"

REM 데이터 전송 대기
timeout /t 2 >nul

echo 3. Streamlit 대시보드 시작 중...
start "Streamlit Dashboard" cmd /k "cd /d "%DASH%" && call "%VENV%\activate" && streamlit run app.py --server.port 8501" 
REM ⬆️ 여기에 닫는 큰따옴표(")가 추가되었습니다!

echo.
echo 🚀 모든 서비스가 실행되었습니다! 창 3개가 떴는지 확인하세요.
pause
```
eof

### 🔍 오류 원인 요약

이전 코드의 오류가 발생한 부분은 다음과 같습니다.

```batch
start "Streamlit Dashboard" cmd /k "cd /d "%DASH%" && call "%VENV%\activate" && streamlit run app.py --server.port 8501