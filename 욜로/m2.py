import cv2
import time
import json
import asyncio
import requests
import numpy as np
from ultralytics import YOLO
import websockets
import winsound

# ------------------ 설정 ------------------
CAM_ID = 2
SERVER_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/data"

# 🔴 [중요] 두 번째 카메라는 장치 번호 1번
WEBCAM_DEVICE_INDEX = 1  
SEND_INTERVAL = 0.05
SHOW_WINDOW = True
DEVICE = 0 

# 🔴 siren.wav 파일 사용 (WAV 변환 필수)
ALARM_SOUND_FILE = "siren.wav"  
ALARM_COOLDOWN = 1.0 

# ✅ winsound를 사용하여 WAV 파일을 재생하는 함수
def play_alarm():
    """WAV 파일을 비동기 방식으로 재생합니다."""
    try:
        winsound.PlaySound(ALARM_SOUND_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"🔊 경고음 재생 실패: {e}. 'siren.wav' 파일이 폴더에 있는지 확인하세요.")

# ✅ 영상 업로드 함수
def upload_frame_sync(cam_id, image_bytes):
    try:
        requests.post(
            f"{SERVER_URL}/upload_frame/{cam_id}",
            files={'file': ('frame.jpg', image_bytes, 'image/jpeg')},
            timeout=0.2
        )
    except Exception:
        pass

async def run_yolo(ws):
    print(f"🚀 YOLO 모델 로딩 중... (GPU) - CAM {CAM_ID}")
    model = YOLO("yolov8n.pt") 

    print(f"📷 CAM {CAM_ID} 연결 시도 중... (Device: {WEBCAM_DEVICE_INDEX})")
    
    cap = cv2.VideoCapture(WEBCAM_DEVICE_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    time.sleep(1)

    if not cap.isOpened():
        print(f"❌ 카메라 {WEBCAM_DEVICE_INDEX}번을 열 수 없습니다.")
        return

    print(f"✅ CAM {CAM_ID} 시작 (GPU 모드)")
    
    last_send = 0.0
    last_alarm_time = 0.0
    is_danger_ever_detected = False 
    
    while True:
        ok, frame = cap.read()
        if not ok:
            print("⚠️ 프레임 읽기 실패")
            break
        
        frame = cv2.flip(frame, 1)

        results = await asyncio.to_thread(
            model, frame, classes=[0, 43, 67], conf=0.3, verbose=False, device=DEVICE
        )
        
        people_count = 0
        is_weapon_detected_now = False

        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                if cls_id == 0: people_count += 1
                elif cls_id in [43, 67]: 
                    is_weapon_detected_now = True

        annotated_frame = results[0].plot()

        # 🔴 [핵심 로직] 영구 지속 위험 상태 및 리셋 로직
        now = time.time()
        
        # 1. 무기 감지 시 영구 위험 상태 설정
        if is_weapon_detected_now:
            is_danger_ever_detected = True

        # 2. 🚨 리셋 조건: 사람이 아무도 없으면 위험 상태 해제
        if people_count == 0:
            is_danger_ever_detected = False
        
        is_danger = is_danger_ever_detected 

        if is_danger:
            cv2.rectangle(annotated_frame, (0, 0), (annotated_frame.shape[1], annotated_frame.shape[0]), (0, 0, 255), 10)
            cv2.putText(annotated_frame, "DANGER DETECTED (ALARM!)", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)

            # 🔊 경보음 울리기 (쿨다운 적용)
            if now - last_alarm_time >= ALARM_COOLDOWN:
                play_alarm()
                last_alarm_time = now

        if now - last_send >= SEND_INTERVAL:
            payload = {
                "cam_id": CAM_ID, 
                "people": people_count, 
                "danger": is_danger, 
                "timestamp": now
            }
            try:
                await ws.send(json.dumps(payload))
                if is_danger: print(f"🚨 [CAM {CAM_ID}] 위험 감지! (영구 지속)")
            except:
                break

            frame_resized = cv2.resize(annotated_frame, (640, 360))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60] 
            _, img_encoded = cv2.imencode('.jpg', frame_resized, encode_param)
            asyncio.create_task(
                asyncio.to_thread(upload_frame_sync, CAM_ID, img_encoded.tobytes())
            )
            last_send = now

        if SHOW_WINDOW:
            cv2.imshow(f"CAM {CAM_ID}", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

async def main():
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                print(f"🔌 CAM {CAM_ID} 서버 연결 성공")
                await run_yolo(ws)
        except Exception as e:
            print(f"⚠️ 연결 대기중... {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())