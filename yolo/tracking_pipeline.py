import numpy as np
from sort.sort import Sort

from yolo.temporal_buffer import TemporalBuffer
from yolo.target_vehicle_selector import (
    select_target_vehicle,
    select_target_sliding,
    select_danger_vehicle,
    select_warning_vehicle,
    get_ego_lane_roi
)

CALIB_COEFF = {
    "Ax": 0.000000311478738,
    "Bx": -0.00000106792259,
    "Cx": -0.000034176958043,
    "Dx": 0.018800906079966,
    "Ex": 0.011209630485790,
    "Fx": -5.889778495587035,

    "Ay": -0.000000308125659,
    "By": 0.000110145428395,
    "Cy": -0.000002393741976,
    "Dy": 0.001256019735776,
    "Ey": -0.092492554428315,
    "Fy": 22.295682060095874
}


def pixel_to_distance_2d(x_pixel, y_pixel, calib):
    Ax = calib["Ax"]
    Bx = calib["Bx"]
    Cx = calib["Cx"]
    Dx = calib["Dx"]
    Ex = calib["Ex"]
    Fx = calib["Fx"]

    Ay = calib["Ay"]
    By = calib["By"]
    Cy = calib["Cy"]
    Dy = calib["Dy"]
    Ey = calib["Ey"]
    Fy = calib["Fy"]

    x_m = Ax*x_pixel**2 + Bx*y_pixel**2 + Cx*x_pixel*y_pixel + Dx*x_pixel + Ex*y_pixel + Fx
    y_m = Ay*x_pixel**2 + By*y_pixel**2 + Cy*x_pixel*y_pixel + Dy*x_pixel + Ey*y_pixel + Fy

    return x_m, y_m

def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter = max(0, xB - xA) * max(0, yB - yA)

    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    return inter / (areaA + areaB - inter + 1e-6)

class TrackingPipeline:
    def __init__(self):
        self.tracker = Sort(
            max_age=30,
            min_hits=3,
            iou_threshold=0.3
        )

        self.temporal_buffer = TemporalBuffer(max_frames=10)
        self.ego_lane_buffer = TemporalBuffer(max_frames=10)
        self.danger_area_buffer = TemporalBuffer(max_frames=10)
        self.warning_area_buffer = TemporalBuffer(max_frames=10)

    def update(self, detections, w, h):
        
        if len(detections) > 0:
            sort_input = np.array([
                d["bbox"] + [d["confidence"]] for d in detections
            ])
        else:
            sort_input = np.empty((0, 5))

        tracks = self.tracker.update(sort_input)

        tracked_objects = []

        for track in tracks:
            x1, y1, x2, y2, track_id = track
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

            best_iou = 0
            obj_class = None
            confidence = 0.0

            for det in detections:
                iou_val = iou([x1, y1, x2, y2], det["bbox"])
                if iou_val > best_iou:
                    best_iou = iou_val
                    obj_class = det["class"]
                    confidence = det["confidence"]

            if obj_class is None:
                continue

            x_m, y_m = pixel_to_distance_2d((x1+x2)/2, y2, CALIB_COEFF)  # titik tengah x, bawah y
            distance_m = y_m
            distance_m = max(distance_m, 0)

            tracked_objects.append({
                "track_id": int(track_id),
                "bbox": (x1, y1, x2, y2),
                "class": obj_class,
                "confidence": round(float(confidence), 2),
                "distance_m": round(float(distance_m), 2)
            })

        ego_lane_target = select_target_vehicle(
            tracked_objects,
            w,
            h
        )

        self.ego_lane_buffer.update(
            [ego_lane_target] if ego_lane_target else []
        )

        stable_ego_lane_target = self.ego_lane_buffer.get_stable_objects()

        danger_vehicle = select_danger_vehicle(tracked_objects, w, h)
        self.danger_area_buffer.update(
            [danger_vehicle] if danger_vehicle else []
        )
        stable_danger_vehicle = self.danger_area_buffer.get_stable_objects()

        warning_vehicle = select_warning_vehicle(tracked_objects, w, h)
        self.warning_area_buffer.update(
            [warning_vehicle] if warning_vehicle else []
        )
        stable_warning_vehicle = self.warning_area_buffer.get_stable_objects()

        nearest_object_list = tracked_objects

        self.temporal_buffer.update(nearest_object_list)
        stable_objects = self.temporal_buffer.get_stable_objects()

        return {
            "tracked_objects": tracked_objects,
            "stable_objects": stable_objects,
            "ego_lane_target": stable_ego_lane_target[0] if stable_ego_lane_target else None,
            "danger_vehicle": stable_danger_vehicle[0] if stable_danger_vehicle else None,
            "warning_vehicle": stable_warning_vehicle[0] if stable_warning_vehicle else None
        }
    
    def update_sliding(self, detections, w, h, left_fit=None, right_fit=None):
        
        if len(detections) > 0:
            sort_input = np.array([
                d["bbox"] + [d["confidence"]] for d in detections
            ])
        else:
            sort_input = np.empty((0, 5))

        tracks = self.tracker.update(sort_input)

        tracked_objects = []

        for track in tracks:
            x1, y1, x2, y2, track_id = track
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

            best_iou = 0
            obj_class = None
            confidence = 0.0

            for det in detections:
                iou_val = iou([x1, y1, x2, y2], det["bbox"])
                if iou_val > best_iou:
                    best_iou = iou_val
                    obj_class = det["class"]
                    confidence = det["confidence"]

            if obj_class is None:
                continue

            x_m, y_m = pixel_to_distance_2d((x1+x2)/2, y2, CALIB_COEFF)  # titik tengah x, bawah y
            distance_m = y_m
            distance_m = max(distance_m, 0)

            tracked_objects.append({
                "track_id": int(track_id),
                "bbox": (x1, y1, x2, y2),
                "class": obj_class,
                "confidence": round(float(confidence), 2),
                "distance_m": round(float(distance_m), 2)
            })

        ego_lane_target = select_target_sliding(
            tracked_objects,
            w,
            h,
            left_fit=left_fit,
            right_fit=right_fit
        )

        self.ego_lane_buffer.update(
            [ego_lane_target] if ego_lane_target else []
        )

        stable_ego_lane_target = self.ego_lane_buffer.get_stable_objects()

        danger_vehicle = select_danger_vehicle(tracked_objects, w, h)
        self.danger_area_buffer.update(
            [danger_vehicle] if danger_vehicle else []
        )
        stable_danger_vehicle = self.danger_area_buffer.get_stable_objects()

        warning_vehicle = select_warning_vehicle(tracked_objects, w, h)
        self.warning_area_buffer.update(
            [warning_vehicle] if warning_vehicle else []
        )
        stable_warning_vehicle = self.warning_area_buffer.get_stable_objects()

        nearest_objects = {}

        for obj in tracked_objects:
            cls = obj["class"]
            y_bottom = obj["bbox"][3]

            if cls not in nearest_objects:
                nearest_objects[cls] = obj
            else:
                if y_bottom > nearest_objects[cls]["bbox"][3]:
                    nearest_objects[cls] = obj

        nearest_object_list = list(nearest_objects.values())

        self.temporal_buffer.update(nearest_object_list)
        stable_objects = self.temporal_buffer.get_stable_objects()

        return {
            "tracked_objects": tracked_objects,
            "stable_objects": stable_objects,
            "ego_lane_target": stable_ego_lane_target[0] if stable_ego_lane_target else None,
            "danger_vehicle": stable_danger_vehicle[0] if stable_danger_vehicle else None,
            "warning_vehicle": stable_warning_vehicle[0] if stable_warning_vehicle else None
        }

