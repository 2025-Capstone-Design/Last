# m.py
import cv2
import time
import json
import asyncio
import yt_dlp
from ultralytics import YOLO
import websockets

# ------------------ 설정 ------------------
URI = "ws://127.0.0.1:8000/ws/data"   # ← 서버 WebSocket 엔드포인트 (프론트와 반드시 일치!)
VIDEO_URL = "https://www.youtube.com/watch?v=S1A49C6V-dg"  # 테스트 영상
SEND_INTERVAL = 0.5  # 초당 2회 전송 (너무 빠르면 끊김 ↑)
CAPACITY = 1200      # 혼잡도(%) 계산용. 서버/프론트 아무 쪽에서나 써도 되지만, 여기서 계산도 함께 보냄.

# 화면에 YOLO 결과를 띄울지 여부
SHOW_WINDOW = True

async def run_yolo(ws):
    """YOLO 추론을 별도 스레드로 돌리고, 결과(사람 수/혼잡도)를 WS로 주기적으로 전송"""
    model = YOLO("yolov8s.pt")

    # 유튜브 스트림 URL 추출
    ydl_opts = {'format': 'best'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(VIDEO_URL, download=False)
        stream_url = info['url']

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print("❌ 영상 스트림을 열 수 없습니다.")
        return

    print("✅ 유튜브 영상 스트림 연결 완료!")
    print("🧠 사람 감지 중... (종료하려면 Q)")

    last_send = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("⚠️ 영상 스트림이 종료되었거나 끊김. 재시도 필요")
                break

            # YOLO 추론을 스레드로 넘겨 event loop 블로킹 방지
            # (ultralytics는 model(image, ...) 호출 형태)
            results = await asyncio.to_thread(
                model, frame, classes=[0], conf=0.3, verbose=False
            )

            # 사람 수 계산 (classes=[0] → 'person'만)
            people = len(results[0].boxes) if results else 0

            # 혼잡도(%): 0~99.9로 캡핑 (그래프 상한 뚫림 방지)
            congestion = 100.0 * people / CAPACITY if CAPACITY > 0 else 0.0
            if not (congestion == congestion):  # NaN 방지
                congestion = 0.0
            congestion = max(0.0, min(99.9, congestion))

            # 전송 주기 제한
            now = time.time()
            if now - last_send >= SEND_INTERVAL:
                payload = {
                    "timestamp": now,        # 선택: 원하면 프론트에서 안 써도 됨
                    "people": int(people),   # ★ 핵심: YOLO에서 센 사람 수
                    "congestion": round(congestion, 1)  # 선택: 퍼센트도 같이 제공(프론트에서 바로 씀)
                }
                await ws.send(json.dumps(payload, ensure_ascii=False))
                last_send = now

            # (옵션) 화면 표시
            if SHOW_WINDOW:
                annotated = results[0].plot()
                cv2.putText(annotated, f"People: {people}", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("YOLO Crowd Detection (YouTube)", annotated)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()

async def main():
    # 끊기면 자동 재연결 루프
    while True:
        try:
            print(f"🔌 WebSocket 연결 시도 -> {URI}")
            async with websockets.connect(
                URI,
                ping_interval=30,
                ping_timeout=60,
                max_queue=None,
            ) as ws:
                print("✅ WebSocket 연결 완료 (FastAPI 서버)")
                await run_yolo(ws)  # 여기서 추론 & 전송
        except Exception as e:
            print(f"⚠️ 연결 에러, 2초 후 재시도: {type(e).__name__}: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
