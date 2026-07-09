import cv2
import numpy as np
from yolo.target_vehicle_selector import get_ego_lane_roi

class PerspectiveTransformer:
    def __init__(self, img_size):
        w, h = img_size

        roi = get_ego_lane_roi(w, h)

        bl, br, tr, tl = roi

        self.src = np.float32([tl, tr, br, bl])

        # TITIK TUJUAN (bird-eye)
        self.dst = np.float32([
            [w * 0.15, 0],
            [w * 0.85, 0],
            [w * 0.85, h],
            [w * 0.15, h]
        ])

        self.M = cv2.getPerspectiveTransform(self.src, self.dst)
        self.M_inv = cv2.getPerspectiveTransform(self.dst, self.src)
    
    def draw_src(self, frame):
        debug = frame.copy()
        pts = self.src.astype(np.int32)

        cv2.polylines(debug, [pts], True, (0, 0, 255), 3)

        for i, (x, y) in enumerate(pts):
            cv2.circle(debug, (int(x), int(y)), 8, (0, 255, 0), -1)
            cv2.putText(debug, f"{i}", (int(x)+5, int(y)-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
        return debug

    def warp(self, img):
        h, w = img.shape[:2]
        return cv2.warpPerspective(img, self.M, (w, h))

    def unwarp(self, img):
        h, w = img.shape[:2]
        return cv2.warpPerspective(img, self.M_inv, (w, h))
