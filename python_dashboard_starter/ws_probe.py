import asyncio, websockets, json, time

async def main():
    uri = "ws://127.0.0.1:8000/ws/data"
    while True:
        try:
            print(f"🔌 연결 시도: {uri}")
            async with websockets.connect(uri, ping_interval=30, ping_timeout=60) as ws:
                print("✅ 연결 성공! 더미 데이터 전송 시작")
                while True:
                    await ws.send(json.dumps({"timestamp": time.time(), "congestion": 55}))
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ 재시도... ({type(e).__name__}: {e})")
            await asyncio.sleep(2)

asyncio.run(main())
