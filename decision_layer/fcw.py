import numpy as np
import time
from yolo.target_vehicle_selector import get_ego_lane_roi

# Y_VALID_MIN = 400
# Y_VALID_MAX = 650

def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_area = max(0, xB - xA) * max(0, yB - yA)

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou_value = inter_area / (boxA_area + boxB_area - inter_area + 1e-6)
    return iou_value

class FCW:
    def __init__(self, iou_threshold=0.5, alpha=0.5):
        self.iou_threshold = iou_threshold
        self.alpha = alpha
        self.prev_confidence = None  # untuk temporal smoothing
        self.prev_positions = {}

    def compute_relative_motion(self, target_obj, image_width=None, image_height=None):
        if target_obj is None:
            return 0.0, 0.0

        x1, y1, x2, y2 = map(float, target_obj["bbox"])
        # y2 = min(max(y2, Y_VALID_MAX), Y_VALID_MIN)
        if image_width is not None and image_height is not None:
            roi = get_ego_lane_roi(image_width, image_height)
            y_values = [p[1] for p in roi]
            y_min = min(y_values)
            y_max = max(y_values)
            y2 = min(max(y2, y_min), y_max)
        relative_distance = y2 - y1

        track_id = target_obj.get("track_id", None)
        prev_y = self.prev_positions.get(track_id, y1)
        relative_speed = y1 - prev_y  # positif = mendekat

        if track_id is not None:
            self.prev_positions[track_id] = y1

        return relative_distance, relative_speed


    def combine_confidence(self, ego_lane_target, stable_objects):
        if ego_lane_target is None:
            if stable_objects:
                target = stable_objects[0]
                conf = target['confidence'] * 0.5
                return target, conf
            else:
                return None, 0.0  # tidak ada target sama sekali

        # ada ego_lane_target
        conf = ego_lane_target['confidence']
        for obj in stable_objects:
            # cek track_id sama
            if obj['track_id'] == ego_lane_target['track_id']:
                conf = min(1.0, conf + obj['confidence'] * self.alpha)
                break
            else:
                # cek IOU
                overlap = iou(ego_lane_target['bbox'], obj['bbox'])
                if overlap < self.iou_threshold:
                    conf *= 0.9
        return ego_lane_target, conf

    def smooth_confidence(self, conf, beta=0.7):
        if self.prev_confidence is None:
            smoothed = conf
        else:
            smoothed = beta * self.prev_confidence + (1 - beta) * conf
        self.prev_confidence = smoothed
        return smoothed

    def run(self, danger_vehicle, warning_vehicle, ego_lane_target, stable_objects, target_obj=None, image_width=None, image_height=None):
        # gabungkan confidence
        target, conf = self.combine_confidence(ego_lane_target, stable_objects)
        relative_distance, relative_speed = self.compute_relative_motion(target, image_width, image_height)

        if danger_vehicle:
            warning_level = 5 #DANGER
            conf = danger_vehicle.get('confidence', 1.0)
            stable_conf = conf > 0.7
            relative_distance = danger_vehicle['bbox'][3] - danger_vehicle['bbox'][1]
            ttc = 0.0
        elif warning_vehicle:
            warning_level = 4 #WARNING
            conf = warning_vehicle.get('confidence', 1.0)
            stable_conf = conf > 0.7
            relative_distance = warning_vehicle['bbox'][3] - warning_vehicle['bbox'][1]
            ttc = 0.0
        else:
            if target is None:
                return {
                    "fcw_active": False,
                    "level": "OFF",
                    "confidence": 0.0,
                    "ttc_proxy": float('inf'),
                    "distance_proxy": 0.0,
                    "stable_conf": False,
                    "timestamp": int(time.time())
                }

            # smooth confidence
            conf = self.smooth_confidence(conf)

            stable_conf = conf > 0.7

            # hitung Time-to-Collision (TTC)
            if relative_speed > 0:  # mendekat
                ttc = relative_distance / (-relative_speed + 1e-6)
            else:
                ttc = float('inf')  # tidak ada risiko

            # level warning
            if ttc < 0.8: #manusia 0.6
                warning_level = 3  # HARD
            elif ttc < 1.5: #manusia 1.2
                warning_level = 2  # MEDIUM
            elif ttc < 2.5: #manusia 2.0
                warning_level = 1  # LOW
            else:
                warning_level = 0  # OFF
        
        level_map = {0: "OFF", 1: "LOW", 2: "MEDIUM", 3: "HARD", 4: "WARNING", 5: "DANGER"}

        brake_decision = {
            "fcw_active": warning_level > 0,            
            "level": level_map[warning_level],
            "confidence": round(conf, 2),           
            "ttc_proxy": ttc,                            
            "distance_proxy": relative_distance,        
            "stable_conf": stable_conf,
            "timestamp": int(time.time())            
        }

        return brake_decision

