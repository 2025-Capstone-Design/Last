import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Realtime Data Server")

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수 (Streamlit 클라이언트 목록)
stream_clients = set()

# -------------------------------
# 1️⃣ YOLO → 서버 데이터 입력
# -------------------------------
@app.websocket("/ws/data")
async def ws_from_yolo(websocket: WebSocket):
    await websocket.accept()
    print("✅ YOLO 연결됨 (데이터 수신 중...)")

    try:
        while True:
            msg = await websocket.receive_text()
            print(f"📥 YOLO 데이터 수신: {msg}")

            # 연결된 Streamlit 클라이언트들에게 브로드캐스트
            for client in list(stream_clients):
                try:
                    await client.send_text(msg)
                except Exception as e:
                    print(f"⚠️ Streamlit 전송 실패 → 제거됨: {e}")
                    stream_clients.remove(client)

    except Exception as e:
        print(f"⚠️ YOLO 연결 예외 발생: {e}")
    finally:
        print("⏳ YOLO 연결 대기 중 (재시도 가능)...")

# -------------------------------
# 2️⃣ Streamlit → 실시간 구독
# -------------------------------
@app.websocket("/ws/stream")
async def ws_to_streamlit(websocket: WebSocket):
    await websocket.accept()
    stream_clients.add(websocket)
    print("📡 Streamlit 연결됨 (그래프 전송 중...)")

    try:
        while True:
            await asyncio.sleep(1)  # Keep alive
    except Exception as e:
        print(f"⚠️ Streamlit 연결 종료: {e}")
    finally:
        stream_clients.remove(websocket)
        await websocket.close()

# -----------------------------
# ✅ 서버 시작 시 메시지
# -----------------------------
@app.on_event("startup")
async def startup_event():
    print("🚀 WebSocket Relay Server Ready (YOLO ↔ Streamlit 병렬 대기)")
