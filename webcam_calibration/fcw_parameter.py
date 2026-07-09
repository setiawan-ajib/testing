Y_VALID_MIN = 400       # pixel di bawah kamera → jarak terdekat 2 m
Y_VALID_MAX = 650       # pixel di bawah kamera → jarak terjauh 10 m
CAMERA_FPS = 28.7       # FPS hasil pengukuran real camera

DISTANCE_M_MIN = 2.0
DISTANCE_M_MAX = 10.0

PIXELS_PER_METER = abs(Y_VALID_MAX - Y_VALID_MIN) / (DISTANCE_M_MAX - DISTANCE_M_MIN)

print("=== COPY-PASTE KE fcw.py ===")
print(f"# Camera FPS (frame per detik)")
print(f"CAMERA_FPS = {CAMERA_FPS:.3f}\n")

print(f"# Pixel range valid (ground calibration)")
print(f"Y_VALID_MIN = {Y_VALID_MIN}")
print(f"Y_VALID_MAX = {Y_VALID_MAX}")
print(f"PIXELS_PER_METER = {PIXELS_PER_METER:.2f}")

print("\n# Example: relative_speed in pixel/frame")
print("# relative_distance = y_bottom - prev_y_bottom")
print("# relative_speed_px = prev_y_bottom - curr_y_bottom")
