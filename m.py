import cv2
import time
import json
import asyncio
import requests
import numpy as np
from ultralytics import YOLO
import websockets
import winsound
import functools

# ------------------ 설정 ------------------
CAM_ID = 1
SERVER_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/data"

# 🔴 0번 카메라 강제 지정
WEBCAM_DEVICE_INDEX = 0  
SEND_INTERVAL = 0.05
SHOW_WINDOW = True
DEVICE = 0 

# 🔴 siren.wav 파일 사용 (WAV 변환 필수)
ALARM_SOUND_FILE = "siren.wav"  
ALARM_COOLDOWN = 1.0 

# ✅ winsound를 사용하여 WAV 파일을 재생하는 함수
def play_alarm():
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

# ✅ 두 박스(사람, 흉기)가 겹치는지 확인하는 함수
def is_overlapping(box1, box2):
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    if x2_1 < x1_2 or x2_2 < x1_1 or y2_1 < y1_2 or y2_2 < y1_1:
        return False
    return True

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
        print("⚠️ 0번 실패. 1번으로 재시도합니다...")
        cap.release()
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
             print("❌ 1번도 실패했습니다. 카메라 연결을 확인하세요.")
             return

    print(f"✅ CAM {CAM_ID} 시작 (GPU 모드 + ByteTrack)")
    
    last_send = 0.0
    last_alarm_time = 0.0
    dangerous_track_ids = set() 
    
    while True:
        ok, frame = cap.read()
        if not ok:
            print("⚠️ 프레임 읽기 실패")
            break
        
        frame = cv2.flip(frame, 1)

        # 🔴 [수정됨] YOLO 추적을 비동기 스레드로 실행 (화면 전송 멈춤 방지)
        # partial을 사용하여 인자 전달 문제를 해결
        run_track = functools.partial(
            model.track, 
            source=frame, 
            classes=[0, 43, 67], 
            conf=0.3, 
            persist=True, 
            tracker="bytetrack.yaml", 
            verbose=False, 
            device=DEVICE
        )
        results = await asyncio.to_thread(run_track)
        
        people_count = 0
        current_danger_detected = False 
        current_people = [] 
        current_weapons = [] 

        if results and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                xyxy = box.xyxy[0].cpu().numpy()

                if cls_id == 0:
                    people_count += 1
                    if box.id is not None:
                        track_id = int(box.id[0])
                        current_people.append((xyxy, track_id))
                elif cls_id in [43, 67]:
                    current_weapons.append(xyxy)

        # 위험 인물 매칭 로직
        for weapon_box in current_weapons:
            for person_box, person_id in current_people:
                if is_overlapping(weapon_box, person_box):
                    dangerous_track_ids.add(person_id)

        # 화면 그리기
        annotated_frame = frame.copy()
        
        for person_box, person_id in current_people:
            x1, y1, x2, y2 = map(int, person_box)
            if person_id in dangerous_track_ids:
                current_danger_detected = True
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 4)
                cv2.putText(annotated_frame, f"DANGER (ID: {person_id})", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            else:
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"Person (ID: {person_id})", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        for w_box in current_weapons:
             x1, y1, x2, y2 = map(int, w_box)
             cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
             cv2.putText(annotated_frame, "WEAPON", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        is_danger = current_danger_detected
        now = time.time()

        if is_danger:
            cv2.rectangle(annotated_frame, (0, 0), (annotated_frame.shape[1], annotated_frame.shape[0]), (0, 0, 255), 10)
            cv2.putText(annotated_frame, "DANGER DETECTED (ALARM!)", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
            if now - last_alarm_time >= ALARM_COOLDOWN:
                play_alarm() 
                last_alarm_time = now

        # 웹소켓 데이터 전송 및 이미지 업로드
        if now - last_send >= SEND_INTERVAL:
            payload = {
                "cam_id": CAM_ID, 
                "people": people_count, 
                "danger": is_danger, 
                "timestamp": now
            }
            try:
                await ws.send(json.dumps(payload))
                if is_danger: print(f"🚨 [CAM {CAM_ID}] 위험 인물 추적 중!")
            except:
                break

            frame_resized = cv2.resize(annotated_frame, (640, 360))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60] 
            _, img_encoded = cv2.imencode('.jpg', frame_resized, encode_param)
            
            # 🔴 [중요] 이미지 업로드를 비동기로 실행
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