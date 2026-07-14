import cv2
from OCR.paddle_engine import PaddleEngine

engine = PaddleEngine()

img = cv2.imread(
    "debug_bib_4.jpg"
)

text, conf = engine.read(img)

print(
    text,
    conf
)