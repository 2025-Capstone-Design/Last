# m.py
import cv2
import time
import json
import asyncio
import yt_dlp
from ultralytics import YOLO
import websockets

URI = "ws://127.0.0.1:8000/ws/data"   # FastAPI 서버 입력 채널
VIDEO_URL = "https://www.youtube.com/watch?v=S1A49C6V-dg"  # 테스트 영상
SEND_INTERVAL = 0.5  # 초당 2회 전송 (너무 빠르면 끊김 빈도↑)

async def run_yolo(ws):
    """YOLO 추론을 별도 스레드에서 돌리고, 결과만 event loop에서 ws로 전송"""
    model = YOLO("yolov8n.pt")

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

            # YOLO 추론을 스레드로 넘김 -> event loop 안 막힘
            results = await asyncio.to_thread(
                model, frame, classes=[0], conf=0.3, verbose=False
            )
            people = len(results[0].boxes) if results else 0

            # 전송 주기 제한
            now = time.time()
            if now - last_send >= SEND_INTERVAL:
                payload = {"timestamp": now, "congestion": people * 5}
                await ws.send(json.dumps(payload))
                last_send = now

            # (옵션) 화면 표시는 동기 호출이라 약간 버벅일 수 있음
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
