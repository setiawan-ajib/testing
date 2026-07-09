import math
import numpy as np
from yolo.tracking_pipeline import pixel_to_distance_2d, CALIB_COEFF
from yolo.target_vehicle_selector import get_ego_lane_roi_center, get_danger_area_roi

def get_x_at_y(lane_points, y_target):
    if not lane_points:
        print("\n[DEBUG NORMALIZE] FAIL: missing lane_points")
        return None

    if len(lane_points) < 5:
        print("\n[DEBUG NORMALIZE] FAIL: lane_points < 5")
        return None

    ys = np.array([p[1] for p in lane_points if p is not None])
    xs = np.array([p[0] for p in lane_points if p is not None])

    if len(ys) < 5:
        return None

    if np.max(ys) - np.min(ys) < 50:
        return None

    if len(np.unique(ys)) < 3:
        return None

    try:
        coeff = np.polyfit(ys, xs, 2)
    except Exception as e:
        print("[DEBUG NORMALIZE] polyfit error:", e)
        return None

    return coeff[0]*y_target**2 + coeff[1]*y_target + coeff[2]

def get_x_from_fit(fit, y):
    if fit is None:
        return None
    return fit[0]*y**2 + fit[1]*y + fit[2]

def normalize_ego_lane(
    lanes_points,
    lanes_detected,
    frame_width,
    frame_height,
    confidence,
    center_offset,
    lane_width_px,
    lane_width_m=3,
    cfg=None
):
    if cfg is None:
        cfg = {}

    # DX_NOISE_GATE = cfg.get("dx_noise_gate",  0.010)
    DX_NOISE_GATE = 0.010
    NORM_CONF_MIN = cfg.get("norm_conf_min",  0.50)

    left_lane = lanes_points[1]
    right_lane = lanes_points[2]

    if not left_lane or not right_lane:
        print("[DEBUG NORMALIZE] FAIL: missing left/right lane")
        return None

    danger_roi = get_danger_area_roi(frame_width, frame_height)

    y_top = int((danger_roi[0][1] + danger_roi[1][1]) / 2)
    y_bottom = int((danger_roi[2][1] + danger_roi[3][1]) / 2)

    y_near = int(y_bottom - 0.25 * (y_bottom - y_top))
    y_far  = int(y_bottom - 0.65 * (y_bottom - y_top))

    safe_lane_width_px = max(lane_width_px, 1e-3)

    px_to_m = lane_width_m / safe_lane_width_px
    px_to_m = np.clip(px_to_m, 0.01, 0.05)

    center_offset_m = center_offset * px_to_m

    x_left_near  = get_x_at_y(left_lane, y_near)
    x_right_near = get_x_at_y(right_lane, y_near)
    x_left_far   = get_x_at_y(left_lane, y_far)
    x_right_far  = get_x_at_y(right_lane, y_far)

    if None in [x_left_near, x_right_near, x_left_far, x_right_far]:
        print("\n[DEBUG NORMALIZE] FAIL: missing near/far points")
        return None

    lane_center_near_px = (x_left_near + x_right_near) / 2
    lane_center_far_px  = (x_left_far + x_right_far) / 2

    dx = lane_center_far_px - lane_center_near_px
    dy = y_far - y_near

    if abs(dy) < 1e-3:
        dy = 1e-3

    heading_error_rad = math.atan2(dx, dy)

    curvature_1pm = 0.0
    if abs(dx) > DX_NOISE_GATE:
        curvature_1pm = dx / (dy * dy)

    if confidence < NORM_CONF_MIN:
        print("\n[DEBUG NORMALIZE] FAIL: low confidence", confidence)
        return None
    
    # print("\n[DEBUG NORMALIZE OK]")
    # print("lateral_offset_m:", center_offset_m)
    # print("heading_error_rad:", heading_error_rad)
    # print("curvature_1pm:", curvature_1pm)
    # print("confidence:", confidence)

    return {
        "lateral_offset_m": float(center_offset_m),
        "heading_error_rad": float(heading_error_rad),
        "curvature_1pm": float(curvature_1pm),
        "confidence": float(confidence)
    }

def normalize_ego_sliding(
    left_fit,
    right_fit,
    frame_width,
    frame_height,
    confidence,
    center_offset,
    lane_width_px,
    lane_width_m=3,
    cfg=None
):
    if cfg is None:
        cfg = {}

    # DX_NOISE_GATE = cfg.get("dx_noise_gate",  0.010)
    DX_NOISE_GATE = 0.010
    NORM_CONF_MIN = cfg.get("norm_conf_min",  0.50)

    if left_fit is None and right_fit is None:
        return None
    
    danger_roi = get_danger_area_roi(frame_width, frame_height)

    y_top = int((danger_roi[0][1] + danger_roi[1][1]) / 2)
    y_bottom  = int((danger_roi[2][1] + danger_roi[3][1]) / 2)

    y_near = int(y_bottom - 0.25 * (y_bottom - y_top))
    y_far  = int(y_bottom - 0.65 * (y_bottom - y_top))

    if left_fit is not None and right_fit is not None:
        x_left_near = get_x_from_fit(left_fit, y_near)
        x_right_near = get_x_from_fit(right_fit, y_near)
        x_left_far = get_x_from_fit(left_fit, y_far)
        x_right_far = get_x_from_fit(right_fit, y_far)

    elif left_fit is None:
        x_right_near = get_x_from_fit(right_fit, y_near)
        x_right_far = get_x_from_fit(right_fit, y_far)

        x_left_near = x_right_near - lane_width_px
        x_left_far = x_right_far - lane_width_px

    elif right_fit is None:
        x_left_near = get_x_from_fit(left_fit, y_near)
        x_left_far = get_x_from_fit(left_fit, y_far)

        x_right_near = x_left_near + lane_width_px
        x_right_far = x_left_far + lane_width_px

    if None in [x_left_near, x_right_near, x_left_far, x_right_far]:
        print("\n[DEBUG NORMALIZE] FAIL: missing near/far points")
        return None
    
    lane_center_near_px = (x_left_near + x_right_near) / 2
    lane_center_far_px = (x_left_far + x_right_far) / 2

    dx = lane_center_far_px - lane_center_near_px
    dy = y_far - y_near

    y_eval = y_near

    if left_fit is not None and right_fit is not None:
        a = (left_fit[0] + right_fit[0]) / 2
        b = (left_fit[1] + right_fit[1]) / 2
    elif left_fit is not None:
        a = left_fit[0]
        b = left_fit[1]
    elif right_fit is not None:
        a = right_fit[0]
        b = right_fit[1]
    else:
        return None

    dx_dy = 2 * a * y_eval + b

    heading_error_rad = math.atan(dx_dy)

    curvature_1pm = 0.0
    if abs(dx) > DX_NOISE_GATE:
        curvature_1pm = dx / (dy * dy)

    if confidence < NORM_CONF_MIN:
        print("\n[DEBUG NORMALIZE] FAIL: low confidence", confidence)
        return None
    
    px_to_m = lane_width_m / lane_width_px
    px_to_m = np.clip(px_to_m, 0.01, 0.05)

    center_offset_m = center_offset * px_to_m
    
    # print("\n[DEBUG NORMALIZE OK]")
    # print("lateral_offset_m:", center_offset_m)
    # print("heading_error_rad:", heading_error_rad)
    # print("curvature_1pm:", curvature_1pm)
    # print("confidence:", confidence)

    return {
        "lateral_offset_m": float(center_offset_m),
        "heading_error_rad": float(heading_error_rad),
        "curvature_1pm": float(curvature_1pm),
        "confidence": float(confidence)
    }