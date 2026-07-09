import cv2
import time

mouse_x, mouse_y = -1, -1
clicked_x, clicked_y = None, None

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y, clicked_x, clicked_y
    mouse_x, mouse_y = x, y

    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_x, clicked_y = x, y
        print(f"[CLICK] x={x}, y={y}")


cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("ERROR: Webcam tidak bisa dibuka")
    exit()

FPS_MEASURE_DURATION = 5.0 
frame_count = 0

print("Measuring camera FPS...")
start_time = time.time()

while time.time() - start_time < FPS_MEASURE_DURATION:
    ret, _ = cap.read()
    if not ret:
        break
    frame_count += 1

camera_fps = frame_count / FPS_MEASURE_DURATION
print(f"[FPS] Camera FPS = {camera_fps:.2f}")

cv2.namedWindow("Webcam")
cv2.setMouseCallback("Webcam", mouse_callback)

print("INFO:")
print("- Geser mouse untuk lihat pixel")
print("- Klik kiri untuk freeze & print koordinat")
print("- Tekan 'q' untuk keluar")
print("- FPS kamera sudah dikunci")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Tampilkan crosshair di mouse
    if mouse_x >= 0 and mouse_y >= 0:
        cv2.drawMarker(
            frame,
            (mouse_x, mouse_y),
            (0, 255, 0),
            markerType=cv2.MARKER_CROSS,
            markerSize=20,
            thickness=1
        )

        cv2.putText(
            frame,
            f"x={mouse_x}, y={mouse_y}",
            (mouse_x + 10, mouse_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )

    # Tampilkan hasil klik
    if clicked_x is not None:
        cv2.circle(frame, (clicked_x, clicked_y), 6, (0, 0, 255), -1)
        cv2.putText(
            frame,
            f"CLICKED: x={clicked_x}, y={clicked_y}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )
    
    # Tampilkan FPS hasil kalibrasi
    cv2.putText(
        frame,
        f"FPS: {camera_fps:.2f}",
        (10, frame.shape[0] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )

    cv2.imshow("Webcam", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("\n=== COPY THIS INTO YOUR CALIBRATION FILE ===")
print(f"CAMERA_FPS = {camera_fps:.3f}")
