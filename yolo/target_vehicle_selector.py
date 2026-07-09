import cv2
import numpy as np
from config import shared_config

TARGET_CLASSES = ["car", "person"]

def get_ego_lane_roi(image_width, image_height, cfg=None):
    if cfg is None:
        cfg = shared_config.get()
    return [
        (int(image_width * cfg.get("roi_ego_bl_x",  0.10)), int(image_height * cfg.get("roi_ego_bl_y",  0.87))),
        (int(image_width * cfg.get("roi_ego_br_x",  0.85)), int(image_height * cfg.get("roi_ego_br_y",  0.87))),
        (int(image_width * cfg.get("roi_ego_tr_x",  0.50)), int(image_height * cfg.get("roi_ego_tr_y",  0.48))),
        (int(image_width * cfg.get("roi_ego_tl_x",  0.47)), int(image_height * cfg.get("roi_ego_tl_y",  0.48))),
    ]

def get_danger_area_roi(image_width, image_height, cfg=None):
    if cfg is None:
        cfg = shared_config.get()
    return [
        (int(image_width * cfg.get("roi_danger_bl_x", 0.20)), int(image_height * cfg.get("roi_danger_bl_y", 0.87))),
        (int(image_width * cfg.get("roi_danger_br_x", 0.80)), int(image_height * cfg.get("roi_danger_br_y", 0.87))),
        (int(image_width * cfg.get("roi_danger_tr_x", 0.60)), int(image_height * cfg.get("roi_danger_tr_y", 0.70))),
        (int(image_width * cfg.get("roi_danger_tl_x", 0.30)), int(image_height * cfg.get("roi_danger_tl_y", 0.70))),
    ]

def get_warning_area_roi(image_width, image_height, cfg=None):
    if cfg is None:
        cfg = shared_config.get()
    return [
        (int(image_width * cfg.get("roi_warn_bl_x", 0.30)), int(image_height * cfg.get("roi_warn_bl_y", 0.70))),
        (int(image_width * cfg.get("roi_warn_br_x", 0.60)), int(image_height * cfg.get("roi_warn_br_y", 0.70))),
        (int(image_width * cfg.get("roi_warn_tr_x", 0.50)), int(image_height * cfg.get("roi_warn_tr_y", 0.55))),
        (int(image_width * cfg.get("roi_warn_tl_x", 0.40)), int(image_height * cfg.get("roi_warn_tl_y", 0.55))),
    ]

def build_ufld_ego_lane_roi(lanes_points, lanes_detected, image_height, max_roi_height_ratio=0.5):
    if lanes_points is None or lanes_detected is None:
        return None
    if len(lanes_points) < 3:
        return None
    if not lanes_detected[1] or not lanes_detected[2]:
        return None
    
    left_lane = lanes_points[1]
    right_lane = lanes_points[2]

    if len(left_lane) < 2 or len(right_lane) < 2:
        return None
    
    min_allowed_y = int(image_height * (1 - max_roi_height_ratio))

    left_filtered = [p for p in left_lane if p[1] >= min_allowed_y]
    right_filtered = [p for p in right_lane if p[1] >= min_allowed_y]

    if len(left_filtered) < 2 or len(right_filtered) < 2:
        return None
    
    left_sorted = sorted(left_filtered, key=lambda p: p[1], reverse=True)
    right_sorted = sorted(right_filtered, key=lambda p: p[1], reverse=True)

    polygon = np.array(
        left_sorted + right_sorted[::-1],
        dtype=np.int32
    )
    return polygon

def build_sliding_ego_lane_roi(left_fit, right_fit, image_height, max_roi_height_ratio=0.5):
    if left_fit is None or right_fit is None:
        return None
    
    min_allowed_y = int(image_height * (1 - max_roi_height_ratio))

    ploty = np.linspace(image_height - 1, min_allowed_y, num=50)

    left_x = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
    right_x = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]

    if np.mean(left_x) > np.mean(right_x):
        return None

    left_pts = np.array(
        [[int(x), int(y)] for x, y in zip(left_x, ploty)]
    )

    right_pts = np.array(
        [[int(x), int(y)] for x, y in zip(right_x, ploty)]
    )
    polygon = np.vstack((left_pts, right_pts[::-1])).astype(np.int32)
    return polygon

def is_vehicle_inside_polygon(bbox, polygon):
    x1, y1, x2, y2 = bbox
    x_center = int((x1 + x2) / 2)
    y_bottom = int(y2)

    return cv2.pointPolygonTest(
        polygon,
        (x_center, y_bottom),
        False
    ) >= 0

def is_vehicle_in_ego_lane(bbox, roi_polygon):
    x1, y1, x2, y2 = bbox
    x_center = int((x1 + x2) / 2)
    y_bottom = int(y2)

    return cv2.pointPolygonTest(
        np.array(roi_polygon, np.int32),
        (x_center, y_bottom),
        False
    ) >= 0

def is_vehicle_in_danger_area(bbox, roi_polygon):
    x1, y1, x2, y2 = bbox
    x_center = int((x1 + x2) / 2)
    y_bottom = int(y2)

    return cv2.pointPolygonTest(
        np.array(roi_polygon, np.int32),
        (x_center, y_bottom),
        False
    ) >= 0

def is_vehicle_in_warning_area(bbox, roi_polygon):
    x1, y1, x2, y2 = bbox
    x_center = int((x1 + x2) / 2)
    y_bottom = int(y2)

    return cv2.pointPolygonTest(
        np.array(roi_polygon, np.int32),
        (x_center, y_bottom),
        False
    ) >= 0


def select_target_vehicle(stable_objects, image_width, image_height, lanes_points=None, lanes_detected=None):
    polygon = build_ufld_ego_lane_roi(lanes_points, lanes_detected, image_height, max_roi_height_ratio=0.5)
    if polygon is None:
        roi = get_ego_lane_roi(image_width, image_height)
        polygon = np.array(roi, np.int32)

    candidates = []

    for obj in stable_objects:
        if obj["class"] not in TARGET_CLASSES:
            continue

        if is_vehicle_inside_polygon(obj["bbox"], polygon):
            candidates.append(obj)

    if not candidates:
        return None

    # kendaraan terdekat = bbox paling bawah
    return max(candidates, key=lambda o: o["bbox"][3])

def select_target_sliding(stable_objects, image_width, image_height, left_fit=None, right_fit=None):
    polygon = build_sliding_ego_lane_roi(left_fit, right_fit, image_height, max_roi_height_ratio=0.5)
    if polygon is None:
        roi = get_ego_lane_roi(image_width, image_height)
        polygon = np.array(roi, np.int32)

    candidates = []

    for obj in stable_objects:
        if obj["class"] not in TARGET_CLASSES:
            continue

        if is_vehicle_inside_polygon(obj["bbox"], polygon):
            candidates.append(obj)

    if not candidates:
        return None

    # kendaraan terdekat = bbox paling bawah
    return max(candidates, key=lambda o: o["bbox"][3])

def select_danger_vehicle(stable_objects, image_width, image_height, cfg=None):  
    roi = get_danger_area_roi(image_width, image_height, cfg=cfg)
    candidates = []

    for obj in stable_objects:
        if obj["class"] not in TARGET_CLASSES:
            continue
        if is_vehicle_in_danger_area(obj["bbox"], roi):
            candidates.append(obj)

    if not candidates:
        return None

    # pilih kendaraan terdekat (bbox paling bawah)
    return max(candidates, key=lambda o: o["bbox"][3])

def select_warning_vehicle(stable_objects, image_width, image_height, cfg=None):
    roi = get_warning_area_roi(image_width, image_height, cfg=cfg)
    candidates = []

    for obj in stable_objects:
        if obj["class"] not in TARGET_CLASSES:
            continue
        if is_vehicle_in_warning_area(obj["bbox"], roi):
            candidates.append(obj)

    if not candidates:
        return None

    # pilih kendaraan terdekat (bbox paling bawah)
    return max(candidates, key=lambda o: o["bbox"][3])


def get_ego_lane_roi_center(image_width, image_height):
    roi = get_ego_lane_roi(image_width, image_height)

    bottom_left, bottom_right = roi[0], roi[1]

    x_coords = (bottom_left[0] + bottom_right[0]) / 2.0
    y_coords = (bottom_left[1] + bottom_right[1]) / 2.0

    return float(x_coords), float(y_coords)

