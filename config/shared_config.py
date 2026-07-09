import threading

_lock = threading.Lock()

_current: dict = {
    # Lane Detection (ego_lane_estimation) 
    "point_density_ref": 120.0,
    "curv_soft": 0.004,
    "curv_hard": 0.010,
    # "curv_noise_gate": 0.003,
    "k_head": 1.0,
    "offset_jump_thresh": 0.10,
    # normalize_ego_lane 
    # "dx_noise_gate": 0.010,
    "k_lat":  0.80,
    "norm_conf_min": 0.50,
    # LKA Control (lka.py)
    "max_rate_deg_per_sec": 15.0,
    "deadzone_heading": 0.25,
    "deadzone_lateral": 0.10,
    # "steer_margin": 0.50,
    "max_lateral_error": 5.0,
    "max_steer_abs": 5.0,
    # Safety LKA (safety_lka.py)
    "safety_min_confidence": 0.70,
    "safety_max_steer_deg": 3.0,
    # ROI – Ego Lane
    "roi_ego_bl_x": 0.10,
    "roi_ego_bl_y": 0.87,
    "roi_ego_br_x": 0.85,
    "roi_ego_br_y": 0.87,
    "roi_ego_tl_x": 0.47,
    "roi_ego_tl_y": 0.48,
    "roi_ego_tr_x": 0.50,
    "roi_ego_tr_y": 0.48,
    # ROI – Danger Area
    "roi_danger_bl_x": 0.20,
    "roi_danger_bl_y": 0.87,
    "roi_danger_br_x": 0.80,
    "roi_danger_br_y": 0.87,
    "roi_danger_tl_x": 0.30,
    "roi_danger_tl_y": 0.70,
    "roi_danger_tr_x": 0.60,
    "roi_danger_tr_y": 0.70,
    # ROI – Warning Area
    "roi_warn_bl_x": 0.30,
    "roi_warn_bl_y": 0.70,
    "roi_warn_br_x": 0.60,
    "roi_warn_br_y": 0.70,
    "roi_warn_tl_x": 0.40,
    "roi_warn_tl_y": 0.55,
    "roi_warn_tr_x": 0.50,
    "roi_warn_tr_y": 0.55,
}


def get() -> dict:
    with _lock:
        return dict(_current)


def update(new_values: dict) -> None:
    with _lock:
        _current.update(new_values)


def reset() -> None:
    defaults = {
        "point_density_ref": 120.0,
        "curv_soft": 0.004,
        "curv_hard": 0.010,
        # "curv_noise_gate": 0.003,
        "k_head": 1.0,
        "offset_jump_thresh": 0.10,
        # "dx_noise_gate": 0.010,
        "k_lat":  0.80,
        "norm_conf_min": 0.50,
        "max_rate_deg_per_sec": 15.0,
        "deadzone_heading": 0.25,
        "deadzone_lateral": 0.10,
        # "steer_margin": 0.50,
        "max_lateral_error": 1.50,
        "max_steer_abs": 5.0,
        "safety_min_confidence": 0.70,
        "safety_max_steer_deg": 3.0,
        "roi_ego_bl_x": 0.10,
        "roi_ego_bl_y": 0.87,
        "roi_ego_br_x": 0.85,
        "roi_ego_br_y": 0.87,
        "roi_ego_tl_x": 0.47,
        "roi_ego_tl_y": 0.48,
        "roi_ego_tr_x": 0.50,
        "roi_ego_tr_y": 0.48,
        "roi_danger_bl_x": 0.20,
        "roi_danger_bl_y": 0.87,
        "roi_danger_br_x": 0.80,
        "roi_danger_br_y": 0.87,
        "roi_danger_tl_x": 0.30,
        "roi_danger_tl_y": 0.70,
        "roi_danger_tr_x": 0.60,
        "roi_danger_tr_y": 0.70,
        "roi_warn_bl_x": 0.30,
        "roi_warn_bl_y": 0.70,
        "roi_warn_br_x": 0.60,
        "roi_warn_br_y": 0.70,
        "roi_warn_tl_x": 0.40,
        "roi_warn_tl_y": 0.55,
        "roi_warn_tr_x": 0.50,
        "roi_warn_tr_y": 0.55,
    }
    with _lock:
        _current.update(defaults)