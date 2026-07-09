import cv2
import numpy as np

video_path = "data/videos/ADAS_testing_video.mp4"  # ganti dengan video kamu
cap = cv2.VideoCapture(video_path)

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:
        print(f"Mouse position: x={x}, y={y}")



while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]

    # ===== ROI (UBAH NILAI INI) =====
    roi = np.array([
        (int(0), int(h * 0.87)),
        (int(w), int(h * 0.87)),
        (int(w * 0.53), int(h * 0.45)),
        (int(w * 0.47), int(h * 0.45))
    ])

    overlay = frame.copy()
    cv2.polylines(overlay, [roi], isClosed=True, color=(0, 255, 0), thickness=2)
    cv2.fillPoly(overlay, [roi], (0, 255, 0))
    frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)

    cv2.imshow("ROI VISUALIZER", frame)
    cv2.setMouseCallback("ROI VISUALIZER", mouse_callback)


    if cv2.waitKey(30) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
