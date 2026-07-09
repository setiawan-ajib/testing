import numpy as np
from yolo.target_vehicle_selector import get_ego_lane_roi_center

prev_center_offset = None
prev_lane_width = None

def estimate_ego_lane_data(lanes_points, lanes_detected, frame_width, frame_height, cfg=None):
    global prev_center_offset

    if cfg is None:
        cfg = {}

    POINT_DENSITY_REF  = cfg.get("point_density_ref",    120.0)
    CURV_SOFT          = cfg.get("curv_soft",             0.004)
    CURV_HARD          = cfg.get("curv_hard",             0.010)
    # CURV_NOISE_GATE    = cfg.get("curv_noise_gate",       0.003)
    CURV_NOISE_GATE = 0.003
    OFFSET_JUMP_THRESH = cfg.get("offset_jump_thresh",    0.10)

    # Default ego lane: lane 1 & 2 (tengah)
    left_lane, right_lane = [], []

    if len(lanes_points) >= 4:
        if lanes_detected[1]:
            left_lane = lanes_points[1]
        if lanes_detected[2]:
            right_lane = lanes_points[2]

    def get_lane_mean_x(lane):
        pts = [pt[0] for pt in lane if pt is not None]
        return np.mean(pts) if pts else None

    left_mean = get_lane_mean_x(left_lane)
    right_mean = get_lane_mean_x(right_lane)

    # validasi posisi
    if left_mean is not None and right_mean is not None:
        if left_mean > right_mean:
            # swap kalau ketukar
            left_lane, right_lane = right_lane, left_lane

    # Hitung center lane
    left_x, right_x = None, None

    if left_lane:
        left_x = np.array([pt[0] for pt in left_lane if pt is not None])

    if right_lane:
        right_x = np.array([pt[0] for pt in right_lane if pt is not None])

    center_x = None

    if left_x is not None and right_x is not None and len(left_x) > 0 and len(right_x) > 0:
        center_x = (np.median(left_x) + np.median(right_x)) / 2

    elif left_x is not None and len(left_x) > 0:
        center_x = np.median(left_x) + frame_width * 0.15

    elif right_x is not None and len(right_x) > 0:
        center_x = np.median(right_x) - frame_width * 0.15

    else:
        return {
            "center_offset": 0.0,
            "curvature": 0.0,
            "confidence": 0.0,
            "center_x": None,
            "ego_center_x": None,
            "lane_width_px": 0.0
        }

    #Y Buckets
    # BIN_SIZE = 10  # pixel tolerance

    # def group_by_y(lane):
    #     groups = {}
    #     for x, y in lane:
    #         key = int(y // BIN_SIZE) * BIN_SIZE
    #         if key not in groups:
    #             groups[key] = []
    #         groups[key].append(x)
    #     return groups

    # left_groups = group_by_y(left_lane)
    # right_groups = group_by_y(right_lane)
    # common_bins = set(left_groups.keys()) & set(right_groups.keys())
    # center_x_list = []

    # for y_bin in common_bins:
    #     lx = np.median(left_groups[y_bin])
    #     rx = np.median(right_groups[y_bin])
    #     center_x_list.append((lx + rx) / 2)
    
    # if len(center_x_list) > 0:
    #     center_x = np.mean(center_x_list)
    # else:
    #     return {"center_offset": 0.0, "curvature": 0.0, "confidence": 0.0}

    # Hitung center offset
    ego_center_x, _ = get_ego_lane_roi_center(frame_width, frame_height)
    center_offset = center_x - ego_center_x

    curvature = 0.0

    # Hitung kelengkungan
    try:
        if left_lane and len(left_lane) >= 3:
            y_vals = np.array([pt[1] for pt in left_lane if pt is not None])
            x_vals = np.array([pt[0] for pt in left_lane if pt is not None])
        elif right_lane and len(right_lane) >= 3:
            y_vals = np.array([pt[1] for pt in right_lane if pt is not None])
            x_vals = np.array([pt[0] for pt in right_lane if pt is not None])
        else:
            y_vals, x_vals = None, None

        if y_vals is not None and len(x_vals) >= 3:
            if len(np.unique(y_vals)) > 2:
                coeffs = np.polyfit(y_vals, x_vals, 2)
                curvature = coeffs[0]

    except Exception as e:
        print("[EGO ERROR] curvature failed:", e)
        curvature = 0.0

    confidence = 0.0

    # lane availability
    if left_lane and right_lane:
        confidence += 0.35
    elif left_lane or right_lane:
        confidence += 0.15
    else:
        confidence = 0.0

    # Point density
    num_points = 0
    if left_lane:
        num_points += len([pt for pt in left_lane if pt is not None])
    if right_lane:
        num_points += len([pt for pt in right_lane if pt is not None])

    confidence += min(num_points / POINT_DENSITY_REF, 0.4)

    # Curvature sanity
    curv_norm = abs(curvature)
    if curv_norm < CURV_SOFT:
        curv_score = 1.0
    elif curv_norm < CURV_HARD:
        curv_score = 1.0 - (curv_norm - CURV_SOFT) / (CURV_HARD - CURV_SOFT)
    else:
        curv_score = 0.0

    confidence += 0.2 * curv_score

    offset_penalty = 0.0

    # norm_offset = abs(center_offset) / (frame_width * 0.5)  # 0..1
    # if abs(curvature) < 0.003:
    #     offset_penalty += np.clip(norm_offset * 0.5, 0.0, 0.5)
    # else:
    #     offset_penalty += np.clip(norm_offset * 0.3, 0.0, 0.3)

    if prev_center_offset is not None:
        if abs(center_offset - prev_center_offset) > frame_width * OFFSET_JUMP_THRESH:
            offset_penalty += 0.3

    prev_center_offset = center_offset

    confidence -= offset_penalty
    confidence = float(np.clip(confidence, 0.0, 1.0))

    lane_width_px = 0.0

    if left_x is not None and right_x is not None and len(left_x) > 0 and len(right_x) > 0:
        lane_width_px = abs(np.median(right_x) - np.median(left_x))

    lane_width_px = max(lane_width_px, 1e-3)
    
    # print("\n[DEBUG EGO EST]")
    # # print("left_lane pts:", len(left_lane) if left_lane else 0)
    # # print("right_lane pts:", len(right_lane) if right_lane else 0)
    # print("center_x:", center_x)
    # print("ego_center_x:", ego_center_x)
    # print("center_offset:", center_offset)
    # print("lane_width_px", lane_width_px)
    # # print("left_x", np.median(left_x))
    # print("right_x", np.median(right_x))
    # print("curvature:", curvature)
    # print("confidence:", confidence)

    return {
        "center_offset": float(center_offset), 
        "curvature": float(curvature), 
        "confidence": confidence,
        "center_x": float(center_x) if center_x is not None else None,
        "ego_center_x": float(ego_center_x),
        "lane_width_px": float(lane_width_px)
    }

def estimate_ego_lane_sliding(left_fit, right_fit, fit_error, frame_width, frame_height, cfg=None):
    global prev_center_offset
    global prev_lane_width
    CURV_SOFT          = cfg.get("curv_soft",             0.004)
    CURV_HARD          = cfg.get("curv_hard",             0.010)
    OFFSET_JUMP_THRESH = cfg.get("offset_jump_thresh",    0.10)
    
    if left_fit is None and right_fit is None:
        return {
            "center_offset": 0.0,
            "curvature": 0.0,
            "confidence": 0.0,
            "center_x": None,
            "ego_center_x": frame_width / 2,
            "lane_width_px": 0.0
        }
    
    y_eval = frame_height

    left_x = None
    right_x = None

    if left_fit is not None:
        left_x = left_fit[0]*y_eval**2 + left_fit[1]*y_eval + left_fit[2]

    if right_fit is not None:
        right_x = right_fit[0]*y_eval**2 + right_fit[1]*y_eval + right_fit[2]

    # Hitung center lane
    center_x = None
    if left_x is not None and right_x is not None:
        center_x = (left_x + right_x) / 2
    elif left_x is not None:
        center_x = left_x + frame_width * 0.15
    elif right_x is not None:
        center_x = right_x - frame_width * 0.15
    else:
        center_x = frame_width / 2

    # Hitung center offset
    ego_center_x = frame_width / 2
    center_offset = center_x - ego_center_x

    # Hitung kelengkungan
    curvature = 0.0
    if left_fit is not None:
        curvature = left_fit[0]
    elif right_fit is not None:
        curvature = right_fit[0]

    confidence = 0.0

    # lane availability
    if left_fit is not None and right_fit is not None:
        confidence += 0.3
    elif left_fit is not None or right_fit is not None:
        confidence += 0.15
    else:
        confidence = 0.0

    # Curvature sanity
    curv_norm = abs(curvature)
    if curv_norm < CURV_SOFT:
        curv_score = 1.0
    elif curv_norm < CURV_HARD:
        curv_score = 1.0 - (curv_norm - CURV_SOFT) / (CURV_HARD - CURV_SOFT)
    else:
        curv_score = 0.0

    confidence += 0.2 * curv_score

    if fit_error is not None:
        fit_score = np.exp(-fit_error * 10)   # smooth decay
        fit_score = np.clip(fit_score, 0.2, 1.0)

        confidence += 0.25 * fit_score

    offset_penalty = 0.0

    if prev_center_offset is not None:
        if abs(center_offset - prev_center_offset) > frame_width * OFFSET_JUMP_THRESH:
            offset_penalty += 0.3

    prev_center_offset = center_offset
    
    lane_width_px = 0.0
    if left_x is not None and right_x is not None:
        lane_width_px = abs(right_x - left_x)
        if prev_lane_width is not None:
            width_diff = abs(lane_width_px - prev_lane_width)

            if width_diff < 30:
                confidence += 0.25   # stabil → tambah confidence
            elif width_diff < 60:
                confidence += 0.1   # agak stabil
            else:
                confidence += -0.1
        prev_lane_width = lane_width_px
    else:
        lane_width_px = 0.0

    confidence -= offset_penalty
    confidence = float(np.clip(confidence, 0.0, 1.0))
    
    # print("\n[DEBUG EGO EST]")
    # # print("left_lane pts:", len(left_lane) if left_lane else 0)
    # # print("right_lane pts:", len(right_lane) if right_lane else 0)
    # print("center_x:", center_x)
    # print("ego_center_x:", ego_center_x)
    # print("center_offset:", center_offset)
    # print("lane_width_px", lane_width_px)
    # # print("left_x", np.median(left_x))
    # print("right_x", np.median(right_x))
    # print("curvature:", curvature)
    # print("confidence:", confidence)
    
    return {
        "center_offset": float(center_offset), 
        "curvature": float(curvature), 
        "confidence": confidence,
        "center_x": float(center_x) if center_x is not None else None,
        "ego_center_x": float(ego_center_x),
        "lane_width_px": float(lane_width_px)
    }

