import time
import math

def rad_to_deg(rad):
    return rad * 180.0 / math.pi

def clamp(val, vmin, vmax):
    return max(vmin, min(vmax, val))

def disable_output(confidence, lateral_error, frame_id, prev_state=None, steering_actual_deg=None):
    return {
        "enable":        False,
        "lateral_error": lateral_error,
        "heading_error": 0.0,
        "confidence":    confidence,
        "timestamp":     time.time(),
        "frame_id":      frame_id,
        "reset":         True,
    }


def lane_keeping_assist(ego_lane_normalized, frame_id, prev_state,
                        steering_actual_deg=None, cfg=None):
    if cfg is None:
        cfg = {}

    CONF_ON  = cfg.get("safety_min_confidence", 0.7)
    # CONF_OFF = 0.60
    MAX_HEADING_MEAS = cfg.get("safety_max_steer_deg",  5.0) #6.0    
    MAX_HEADING_CMD  = cfg.get("safety_max_steer_deg",  5.0)
    MAX_LATERAL_ERROR    = cfg.get("max_lateral_error",      5.0)
    # MAX_LATERAL_SAFE = 0.30   
    # FAIL_LATERAL     = 0.40   
    # MAX_LAT_CONTRIB = 3.0
    DRIVER_THRESHOLD = 0.3
    K_HEAD = cfg.get("k_head", 1.0)
    K_LAT  = cfg.get("k_lat",  0.8)
    MAX_RATE_DEG_PER_SEC = cfg.get("max_rate_deg_per_sec", 15.0)
    DEADZONE_HEADING     = cfg.get("deadzone_heading",      0.25)
    DEADZONE_LATERAL     = cfg.get("deadzone_lateral",      0.10)
    STEER_MARGIN         = cfg.get("steer_margin",          0.50)
    MAX_STEER_ABS        = cfg.get("safety_max_steer_deg",  5.0)

    now = time.time()
    prev_ts = prev_state.get("timestamp", now)
    dt = clamp(now - prev_ts, 0.01, 0.2)

    confidence = ego_lane_normalized["confidence"]
    lateral_error = ego_lane_normalized["lateral_offset_m"]
    heading_meas = rad_to_deg(ego_lane_normalized["heading_error_rad"])

    if abs(lateral_error) > MAX_LATERAL_ERROR:  # meter, impossible
        return disable_output(confidence, lateral_error, frame_id, prev_state, steering_actual_deg) 
    
    enable = confidence >= CONF_ON

    # if abs(lateral_error) > FAIL_LATERAL:
    #     return disable_output(confidence, lateral_error, frame_id, prev_state, steering_actual_deg)

    # if abs(lateral_error) > MAX_LATERAL_SAFE:
    #     lateral_error = clamp(lateral_error, -MAX_LATERAL_SAFE, MAX_LATERAL_SAFE)

    heading_meas = clamp(heading_meas, -MAX_HEADING_MEAS, MAX_HEADING_MEAS)

    gain = clamp(confidence / CONF_ON, 0.0, 1.0)

    if steering_actual_deg is not None:
        remaining = MAX_STEER_ABS - abs(steering_actual_deg)
        if remaining < STEER_MARGIN:
            gain *= clamp(remaining / STEER_MARGIN, 0.0, 1.0)

                 

    desired_cmd = K_HEAD * heading_meas + K_LAT * lateral_error
    
    if not prev_state or not prev_state.get("enable", False):
        prev_heading = 0.0
    else:
        prev_heading = prev_state.get("heading_error", 0.0)

    max_delta = MAX_RATE_DEG_PER_SEC * dt

    delta = clamp(desired_cmd - prev_heading, -max_delta, max_delta)
    heading_cmd = prev_heading + delta

    if steering_actual_deg is not None and abs(heading_cmd) > DRIVER_THRESHOLD:
        if abs(steering_actual_deg) > DRIVER_THRESHOLD:
            if math.copysign(1, heading_cmd) != math.copysign(1, steering_actual_deg):
                return disable_output(confidence, lateral_error, frame_id, prev_state, steering_actual_deg)

    # if abs(lateral_error) < 0.15:
    #     K_LAT = 0.5
    # elif abs(lateral_error) < 0.25:
    #     K_LAT = 0.8
    # else:
    #     K_LAT = 1.0

    # lat_term = K_LAT * lateral_error
    # lat_term = clamp(lat_term, -MAX_LAT_CONTRIB, MAX_LAT_CONTRIB)

    # heading_cmd += lat_term

    
    # Deadzone suppression
    if abs(heading_cmd) < DEADZONE_HEADING and abs(lateral_error) < DEADZONE_LATERAL:
        heading_cmd = 0.0

    # if confidence < CONF_OFF:
    #     return disable_output(confidence, lateral_error, frame_id, prev_state, steering_actual_deg)

    heading_cmd *= gain
    heading_cmd = clamp(heading_cmd, -MAX_HEADING_CMD, MAX_HEADING_CMD)

    prev_state["enable"] = enable
    prev_state["heading_error"] = heading_cmd
    prev_state["timestamp"] = now

    return {
        "enable": enable,
        "lateral_error": lateral_error,
        "heading_error": heading_cmd,
        "confidence": confidence,
        "timestamp": now,
        "frame_id": frame_id
    }
