# test_cam.py (카메라 번호 찾기용)
import cv2

print("📷 연결된 카메라를 검색합니다...")

# 0번부터 4번까지 확인
for index in range(5):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ 카메라 {index}번: 정상 작동 중 (해상도: {frame.shape[1]}x{frame.shape[0]})")
        else:
            print(f"⚠️ 카메라 {index}번: 열리긴 했으나 화면이 안 나옴")
        cap.release()
    else:
        print(f"❌ 카메라 {index}번: 연결 안 됨")

print("검색 종료.")