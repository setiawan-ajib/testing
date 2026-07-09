# polynomial_calibration.py
import numpy as np

# MASUKKAN DATA KALIBRASI DI SINI
# Jarak nyata (meter)
distances = np.array([1.0, 1.5, 2.0, 2.5, 3.0])

# Nilai y2 pixel dari deteksi bounding box di masing-masing jarak
# Ganti dengan hasil pengukuran kalian
pixels_y2 = np.array([301, 253, 221, 198, 180])

# FIT POLYNOMIAL ORDER 2 (y^2 + y + C)
# np.polyfit(x, y, deg)
# x = pixels, y = jarak
coeffs = np.polyfit(pixels_y2, distances, 2)

A, B, C = coeffs

print("Koefisien polynomial (distance = A*y^2 + B*y + C):")
print(f"A = {A}")
print(f"B = {B}")
print(f"C = {C}")

# Contoh cek hasil
print("\nCek hasil prediksi jarak:")
for y2, real_dist in zip(pixels_y2, distances):
    predicted = A*y2**2 + B*y2 + C
    print(f"Pixel {y2} → prediksi {predicted:.3f} m, sebenarnya {real_dist} m")