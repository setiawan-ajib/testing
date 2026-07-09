import cv2
import numpy as np
import argparse

# =========================
# ROI DEFINITIONS
# =========================
def get_ego_lane_roi(w, h):
    return np.array([
        (int(w * 0.1), int(h * 0.87)),
        (int(w * 0.85), int(h * 0.87)),
        (int(w * 0.5), int(h * 0.48)),
        (int(w * 0.47), int(h * 0.48))
    ])

def get_danger_area_roi(w, h):
    return np.array([
        (int(w * 0.2), int(h * 0.87)),
        (int(w * 0.8), int(h * 0.87)),
        (int(w * 0.6), int(h * 0.7)),
        (int(w * 0.3), int(h * 0.7))
    ])

def get_warning_area_roi(w, h):
    return np.array([
        (int(w * 0.3), int(h * 0.7)),
        (int(w * 0.6), int(h * 0.7)),
        (int(w * 0.5), int(h * 0.55)),
        (int(w * 0.4), int(h * 0.55))
    ])

# =========================
# DRAW FUNCTION
# =========================
def draw_roi(frame):
    h, w = frame.shape[:2]

    ego = get_ego_lane_roi(w, h)
    danger = get_danger_area_roi(w, h)
    warning = get_warning_area_roi(w, h)

    overlay = frame.copy()

    # Fill transparan
    cv2.fillPoly(overlay, [ego], (0, 255, 0))
    cv2.fillPoly(overlay, [danger], (0, 0, 255))
    cv2.fillPoly(overlay, [warning], (0, 255, 255))

    alpha = 0.25
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Outline
    cv2.polylines(frame, [ego], True, (0, 255, 0), 2)
    cv2.polylines(frame, [danger], True, (0, 0, 255), 2)
    cv2.polylines(frame, [warning], True, (0, 255, 255), 2)

    # Label
    cv2.putText(frame, "EGO", tuple(ego[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    cv2.putText(frame, "DANGER", tuple(danger[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
    cv2.putText(frame, "WARNING", tuple(warning[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

    # Info ukuran
    cv2.putText(frame, f"Resolution: {w}x{h}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    return frame

# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, default="0",
                        help="0 = webcam, atau path video/jpg")
    args = parser.parse_args()

    # Tentukan source
    if args.source.isdigit():
        cap = cv2.VideoCapture(int(args.source))
        is_image = False
    else:
        # cek apakah gambar
        if args.source.lower().endswith((".jpg", ".png", ".jpeg")):
            frame = cv2.imread(args.source)
            is_image = True
        else:
            cap = cv2.VideoCapture(args.source)
            is_image = False

    print("Controls:")
    print("  q = keluar")
    print("  s = save frame")

    while True:
        if is_image:
            display = draw_roi(frame.copy())
        else:
            ret, frame = cap.read()
            if not ret:
                break
            display = draw_roi(frame)

        cv2.imshow("ROI Debug", display)

        key = cv2.waitKey(0 if is_image else 1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("roi_debug_capture.jpg", display)
            print("Saved: roi_debug_capture.jpg")

        if is_image:
            break

    if not is_image:
        cap.release()

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()