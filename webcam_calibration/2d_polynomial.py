# polynomial_calibration_2d_hardcode.py
import numpy as np

# =========================
# 1. MASUKKAN DATA KALIBRASI
# =========================

# Jarak nyata tiap garis horizontal (meter)
distances = [3, 4, 5, 6, 7]  # bisa diganti sesuai kebutuhan

# Setiap garis horizontal: [(x_start_pixel, y_pixel), (x_end_pixel, y_pixel)]
# Ganti dengan hasil ukur kalian
lines_pixels = [
    [(47,388), (216,390), (303,392), (388,394), (562,396)], #1m
    [(100,324), (236,327), (303,328), (368,330), (511,331)], #2m
    [(135,282), (248,284), (304,283), (359,284), (474,286)], #3m
    [(160,253), (258,254), (305,255), (352,255), (447,255)], #4m
    [(178,229), (265,232), (307,233), (347,234), (430,233)]  #5m
]

x_real = [-1.5, -0.5, 0.0, 0.5, 1.5]

# =========================
# 2. BUAT TITIK KALIBRASI
# =========================

x_pixels = []
y_pixels = []
x_meters = []
y_meters = []

for idx, line in enumerate(lines_pixels):
    for i, (x_pixel, y_pixel) in enumerate(line):
        x_pixels.append(x_pixel)
        y_pixels.append(y_pixel)
        x_meters.append(x_real[i])
        y_meters.append(distances[idx])

# ubah ke numpy array
x_pixels = np.array(x_pixels)
y_pixels = np.array(y_pixels)
x_meters = np.array(x_meters)
y_meters = np.array(y_meters)

# =========================
# 3. FIT 2D POLYNOMIAL MENGGUNAKAN NUMPY
# =========================

# Matriks fitur polynomial 2D: x^2, y^2, xy, x, y, 1
X = np.vstack([x_pixels**2, y_pixels**2, x_pixels*y_pixels, x_pixels, y_pixels, np.ones_like(x_pixels)]).T

# Fit untuk x_meter
coeffs_x, *_ = np.linalg.lstsq(X, x_meters, rcond=None)
# Fit untuk y_meter
coeffs_y, *_ = np.linalg.lstsq(X, y_meters, rcond=None)

x_pred = X @ coeffs_x
y_pred = X @ coeffs_y

rmse_x = np.sqrt(np.mean((x_pred - x_meters)**2))
rmse_y = np.sqrt(np.mean((y_pred - y_meters)**2))

print("===== ERROR =====")
print(f"RMSE X (meter): {rmse_x:.4f}")
print(f"RMSE Y (meter): {rmse_y:.4f}")

# =========================
# 4. CETAK KOEFISIEN UNTUK HARD CODE
# =========================

print("===== KOEFISIEN HARD CODE 2D POLYNOMIAL =====")
print("x_meter = Ax*x^2 + Bx*y^2 + Cx*x*y + Dx*x + Ex*y + Fx")
for name, val in zip(["Ax","Bx","Cx","Dx","Ex","Fx"], coeffs_x):
    print(f"{name} = {val:.15f}")

print("\ny_meter = Ay*x^2 + By*y^2 + Cy*x*y + Dy*x + Ey*y + Fy")
for name, val in zip(["Ay","By","Cy","Dy","Ey","Fy"], coeffs_y):
    print(f"{name} = {val:.15f}")