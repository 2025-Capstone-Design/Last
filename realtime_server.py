import asyncio
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(title="Realtime Video & Data Server")

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 📸 영상 스트리밍 저장소 (메모리)
# ---------------------------------------------------------
# 카메라별 최신 프레임을 저장하는 딕셔너리
latest_frames = {
    1: None,  # CAM 1
    2: None   # CAM 2
}

# -------------------------------
# 1️⃣ [영상 업로드] m.py -> 서버 (이미지 전송)
# -------------------------------
@app.post("/upload_frame/{cam_id}")
async def upload_frame(cam_id: int, file: UploadFile = File(...)):
    """
    m.py에서 보낸 이미지를 받아서 최신 프레임으로 저장
    """
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 메모리에 저장
    latest_frames[cam_id] = frame
    return {"status": "received"}

# -------------------------------
# 2️⃣ [영상 송출] 서버 -> Streamlit (영상 보기)
# -------------------------------
def generate_frames(cam_id):
    while True:
        frame = latest_frames.get(cam_id)
        if frame is None:
            # 영상이 없으면 빈 화면(검은색) 송출 대신 잠시 대기
            cv2.waitKey(100) 
            continue
            
        # 이미지를 JPG로 인코딩
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # MJPEG 스트리밍 형식으로 반환
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video_feed/{cam_id}")
async def video_feed(cam_id: int):
    """
    Streamlit에서 이 주소(img src)를 부르면 영상을 실시간으로 보여줌
    """
    return StreamingResponse(generate_frames(cam_id), media_type="multipart/x-mixed-replace; boundary=frame")


# -------------------------------
# 3️⃣ [데이터] WebSocket (기존 코드 유지)
# -------------------------------
stream_clients = set()

@app.websocket("/ws/data")
async def ws_from_yolo(websocket: WebSocket):
    await websocket.accept()
    print("✅ YOLO 데이터 연결됨")
    try:
        while True:
            msg = await websocket.receive_text()
            # Streamlit 클라이언트들에게 브로드캐스트
            for client in list(stream_clients):
                try:
                    await client.send_text(msg)
                except:
                    stream_clients.remove(client)
    except Exception:
        pass

@app.websocket("/ws/stream")
async def ws_to_streamlit(websocket: WebSocket):
    await websocket.accept()
    stream_clients.add(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except:
        stream_clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)