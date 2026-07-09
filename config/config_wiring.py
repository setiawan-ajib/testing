from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import QLocale

# Panel Configuration (Control/Steering + Obstacle/Safety + Geometry)
PARAM_CONFIG_MAIN = {
    # Control & Steering Tuning
    "spinSteeringResp":         (1.0,    0.1,  2),
    "spinSteadyState":          (0.5,    0.1,  2),
    "spinDamping":              (0.8,    0.1,  2),
    "spinCorrectionLimit":      (30.0,   1.0,  1),
    "spinSteeringCenterOffset": (0.0,    0.5,  1),
    "spinBrakingLatency":       (200.0,  10.0, 0), 
    # Obstacle & Safety Sensing
    # "spinObstacleBuffer":       (2.0,    0.5,  2),
    # "spinSensitivity":          (0.5,    0.05, 2),
    # "spinTTC":                  (2.5,    0.1,  1),
    # Geometry & Scale Calibration
    # "spinVehicleWidth":         (1.8,    0.05, 2),
    # "spinScaleFactor":          (50.0,   1.0,  2),
    # "spinCameraHeight":         (1.2,    0.05, 2),
    # "spinLookAhead":            (15.0,   0.5,  1),
}

# Panel Lane Detection & LKA
PARAM_CONFIG_LANE_LKA = {
    # Lane Detection Tuning (ego_lane_estimation)
    "spinPointDensityRef":      (120.0,  5.0,   0),
    "spinCurvSoft":             (0.004,  0.001, 3),
    "spinCurvHard":             (0.010,  0.001, 3),
    # "spinCurvNoiseGate":        (0.003,  0.001, 3),
    "spinKHead":                (1.0,    0.05,  2),
    "spinOffsetJumpThresh":     (0.10,   0.01,  2),
    # normalize_ego_lane
    # "spinDxNoiseGate":          (0.010,  0.005, 3),
    "spinKLat":                 (0.8,    0.05,  2),
    "spinNormConfMin":          (0.50,   0.05,  2),
    # LKA Control Parameters
    "spinMaxRateDeg":           (15.0,   1.0,   1),
    "spinDeadzoneHeading":      (0.25,   0.05,  2),
    "spinDeadzoneLateral":      (0.10,   0.01,  2),
    # "spinSteerMargin":          (0.50,   0.05,  2),
    "spinMaxLateralError":      (5.0,   0.05,  2),
    "spinMaxSteerAbs":          (5.0,    0.5,   1),
    # safety_lka
    "spinSafetyMinConf":        (0.70,   0.05,  2),
    "spinSafetyMaxSteer":       (3.0,    0.5,   1),
    # ROI – Ego Lane
    "spinRoiEgoBlX":   (0.10, 0.01, 2),
    "spinRoiEgoBlY":   (0.87, 0.01, 2),
    "spinRoiEgoBrX":   (0.85, 0.01, 2),
    "spinRoiEgoBrY":   (0.87, 0.01, 2),
    "spinRoiEgoTlX":   (0.47, 0.01, 2),
    "spinRoiEgoTlY":   (0.48, 0.01, 2),
    "spinRoiEgoTrX":   (0.50, 0.01, 2),
    "spinRoiEgoTrY":   (0.48, 0.01, 2),
    # ROI – Danger Area
    "spinRoiDangerBlX": (0.20, 0.01, 2),
    "spinRoiDangerBlY": (0.87, 0.01, 2),
    "spinRoiDangerBrX": (0.80, 0.01, 2),
    "spinRoiDangerBrY": (0.87, 0.01, 2),
    "spinRoiDangerTlX": (0.30, 0.01, 2),
    "spinRoiDangerTlY": (0.70, 0.01, 2),
    "spinRoiDangerTrX": (0.60, 0.01, 2),
    "spinRoiDangerTrY": (0.70, 0.01, 2),
    # ROI – Warning Area
    "spinRoiWarnBlX":  (0.30, 0.01, 2),
    "spinRoiWarnBlY":  (0.70, 0.01, 2),
    "spinRoiWarnBrX":  (0.60, 0.01, 2),
    "spinRoiWarnBrY":  (0.70, 0.01, 2),
    "spinRoiWarnTlX":  (0.40, 0.01, 2),
    "spinRoiWarnTlY":  (0.55, 0.01, 2),
    "spinRoiWarnTrX":  (0.50, 0.01, 2),
    "spinRoiWarnTrY":  (0.55, 0.01, 2),
}

PARAM_CONFIG = {**PARAM_CONFIG_MAIN, **PARAM_CONFIG_LANE_LKA}

BUTTON_PAIRS_MAIN = [
    # Control & Steering
    ("btnSteeringRespMinus",         "spinSteeringResp",          "btnSteeringRespPlus"),
    ("btnSteadyStateMinus",          "spinSteadyState",           "btnSteadyStatePlus"),
    ("btnDampingMinus",              "spinDamping",               "btnDampingPlus"),
    ("btnCorrectionLimitMinus",      "spinCorrectionLimit",       "btnCorrectionLimitPlus"),
    ("btnSteeringCenterOffsetMinus", "spinSteeringCenterOffset",  "btnSteeringCenterOffsetPlus"),
    ("btnBrakingLatencyMinus",       "spinBrakingLatency",        "btnBrakingLatencyPlus"),
    # Obstacle & Safety
    # ("btnObstacleBufferMinus",       "spinObstacleBuffer",        "btnObstacleBufferPlus"),
    # ("btnSensitivityMinus",          "spinSensitivity",           "btnSensitivityPlus"),
    # ("btnTTCMinus",                  "spinTTC",                   "btnTTCPlus"),
    # Geometry
    # ("btnVehicleWidthMinus",         "spinVehicleWidth",          "btnVehicleWidthPlus"),
    # ("btnScaleFactorMinus",          "spinScaleFactor",           "btnScaleFactorPlus"),
    # ("btnCameraHeightMinus",         "spinCameraHeight",          "btnCameraHeightPlus"),
    # ("btnLookAheadMinus",            "spinLookAhead",             "btnLookAheadPlus"),
]

BUTTON_PAIRS_LANE_LKA = [
    # Lane Detection
    ("btnPointDensityRefMinus",      "spinPointDensityRef",       "btnPointDensityRefPlus"),
    ("btnCurvSoftMinus",             "spinCurvSoft",              "btnCurvSoftPlus"),
    ("btnCurvHardMinus",             "spinCurvHard",              "btnCurvHardPlus"),
    # ("btnCurvNoiseGateMinus",        "spinCurvNoiseGate",         "btnCurvNoiseGatePlus"),
    ("btnKHeadMinus",                "spinKHead",                 "btnKHeadPlus"),
    ("btnOffsetJumpThreshMinus",     "spinOffsetJumpThresh",      "btnOffsetJumpThreshPlus"),
    # ("btnDxNoiseGateMinus",          "spinDxNoiseGate",           "btnDxNoiseGatePlus"),
    ("btnKLatMinus",                 "spinKLat",                   "btnKLatPlus"),
    ("btnNormConfMinMinus",          "spinNormConfMin",           "btnNormConfMinPlus"),
    # LKA Control
    ("btnMaxRateDegMinus",           "spinMaxRateDeg",            "btnMaxRateDegPlus"),
    ("btnDeadzoneHeadingMinus",      "spinDeadzoneHeading",       "btnDeadzoneHeadingPlus"),
    ("btnDeadzoneLateralMinus",      "spinDeadzoneLateral",       "btnDeadzoneLateralPlus"),
    # ("btnSteerMarginMinus",          "spinSteerMargin",           "btnSteerMarginPlus"),
    ("btnMaxLateralErrorMinus",      "spinMaxLateralError",       "btnMaxLateralErrorPlus"),
    ("btnMaxSteerAbsMinus",          "spinMaxSteerAbs",           "btnMaxSteerAbsPlus"),
    ("btnSafetyMinConfMinus",        "spinSafetyMinConf",         "btnSafetyMinConfPlus"),
    ("btnSafetyMaxSteerMinus",       "spinSafetyMaxSteer",        "btnSafetyMaxSteerPlus"),
    # ROI – Ego Lane
    ("btnRoiEgoBlXMinus",    "spinRoiEgoBlX",    "btnRoiEgoBlXPlus"),
    ("btnRoiEgoBlYMinus",    "spinRoiEgoBlY",    "btnRoiEgoBlYPlus"),
    ("btnRoiEgoBrXMinus",    "spinRoiEgoBrX",    "btnRoiEgoBrXPlus"),
    ("btnRoiEgoBrYMinus",    "spinRoiEgoBrY",    "btnRoiEgoBrYPlus"),
    ("btnRoiEgoTlXMinus",    "spinRoiEgoTlX",    "btnRoiEgoTlXPlus"),
    ("btnRoiEgoTlYMinus",    "spinRoiEgoTlY",    "btnRoiEgoTlYPlus"),
    ("btnRoiEgoTrXMinus",    "spinRoiEgoTrX",    "btnRoiEgoTrXPlus"),
    ("btnRoiEgoTrYMinus",    "spinRoiEgoTrY",    "btnRoiEgoTrYPlus"),
    # ROI – Danger Area
    ("btnRoiDangerBlXMinus", "spinRoiDangerBlX", "btnRoiDangerBlXPlus"),
    ("btnRoiDangerBlYMinus", "spinRoiDangerBlY", "btnRoiDangerBlYPlus"),
    ("btnRoiDangerBrXMinus", "spinRoiDangerBrX", "btnRoiDangerBrXPlus"),
    ("btnRoiDangerBrYMinus", "spinRoiDangerBrY", "btnRoiDangerBrYPlus"),
    ("btnRoiDangerTlXMinus", "spinRoiDangerTlX", "btnRoiDangerTlXPlus"),
    ("btnRoiDangerTlYMinus", "spinRoiDangerTlY", "btnRoiDangerTlYPlus"),
    ("btnRoiDangerTrXMinus", "spinRoiDangerTrX", "btnRoiDangerTrXPlus"),
    ("btnRoiDangerTrYMinus", "spinRoiDangerTrY", "btnRoiDangerTrYPlus"),
    # ROI – Warning Area
    ("btnRoiWarnBlXMinus",   "spinRoiWarnBlX",   "btnRoiWarnBlXPlus"),
    ("btnRoiWarnBlYMinus",   "spinRoiWarnBlY",   "btnRoiWarnBlYPlus"),
    ("btnRoiWarnBrXMinus",   "spinRoiWarnBrX",   "btnRoiWarnBrXPlus"),
    ("btnRoiWarnBrYMinus",   "spinRoiWarnBrY",   "btnRoiWarnBrYPlus"),
    ("btnRoiWarnTlXMinus",   "spinRoiWarnTlX",   "btnRoiWarnTlXPlus"),
    ("btnRoiWarnTlYMinus",   "spinRoiWarnTlY",   "btnRoiWarnTlYPlus"),
    ("btnRoiWarnTrXMinus",   "spinRoiWarnTrX",   "btnRoiWarnTrXPlus"),
    ("btnRoiWarnTrYMinus",   "spinRoiWarnTrY",   "btnRoiWarnTrYPlus"),
]

BUTTON_PAIRS = BUTTON_PAIRS_MAIN + BUTTON_PAIRS_LANE_LKA

def _get_val(widget) -> float:
    try:
        return float(widget.text().replace(",", "."))
    except (ValueError, AttributeError):
        return 0.0


def _set_val(widget, value: float, decimals: int):
    fmt = f"{{:.{decimals}f}}"
    widget.setText(fmt.format(value))


def _make_step_fn(win, lineedit_name: str, direction: int):
    _default, step, decimals = PARAM_CONFIG[lineedit_name]
    def _step():
        widget = getattr(win, lineedit_name)
        new_val = _get_val(widget) + direction * step
        _set_val(widget, new_val, decimals)
    return _step


def _wire_panel(win, param_dict, button_pairs):
    locale = QLocale(QLocale.C)
    locale.setNumberOptions(QLocale.RejectGroupSeparator)

    for name, (default, _step, decimals) in param_dict.items():
        widget = getattr(win, name, None)
        if widget is None:
            continue
        validator = QDoubleValidator(-1e300, 1e300, 10)
        validator.setLocale(locale)
        validator.setNotation(QDoubleValidator.StandardNotation)
        widget.setValidator(validator)
        _set_val(widget, default, decimals)

    for btn_minus_name, lineedit_name, btn_plus_name in button_pairs:
        btn_minus = getattr(win, btn_minus_name, None)
        btn_plus  = getattr(win, btn_plus_name,  None)
        if btn_minus:
            btn_minus.clicked.connect(_make_step_fn(win, lineedit_name, -1))
        if btn_plus:
            btn_plus.clicked.connect(_make_step_fn(win, lineedit_name, +1))


#  PUBLIC API
def wire_config_panel(win) -> None:
    _wire_panel(win, PARAM_CONFIG_MAIN, BUTTON_PAIRS_MAIN)


def wire_lane_lka_panel(win) -> None:
    _wire_panel(win, PARAM_CONFIG_LANE_LKA, BUTTON_PAIRS_LANE_LKA)


#  GET/SET/RESET  – Panel (Configuration)
def get_config_values(win) -> dict:
    return {
        # Control & Steering
        "steering_responsiveness":   _get_val(win.spinSteeringResp),
        "steady_state_correction":   _get_val(win.spinSteadyState),
        "damping_stability":         _get_val(win.spinDamping),
        "correction_limit":          _get_val(win.spinCorrectionLimit),
        "steering_center_offset":    _get_val(win.spinSteeringCenterOffset),
        "braking_latency_ms":        _get_val(win.spinBrakingLatency), 
        # Obstacle & Safety 
        # "obstacle_detection_buffer": _get_val(win.spinObstacleBuffer),
        # "sensitivity_threshold":     _get_val(win.spinSensitivity),
        # "collision_warning_ttc_s":   _get_val(win.spinTTC),
        # Geometry 
        # "vehicle_reference_width_m": _get_val(win.spinVehicleWidth),
        # "scale_factor_px_m":         _get_val(win.spinScaleFactor),
        # "camera_mounting_height_m":  _get_val(win.spinCameraHeight),
        # "look_ahead_distance_m":     _get_val(win.spinLookAhead),
    }


def set_config_values(win, cfg: dict) -> None:
    mapping = {
        # Control & Steering
        "steering_responsiveness":   ("spinSteeringResp",          2),
        "steady_state_correction":   ("spinSteadyState",           2),
        "damping_stability":         ("spinDamping",               2),
        "correction_limit":          ("spinCorrectionLimit",       1),
        "steering_center_offset":    ("spinSteeringCenterOffset",  1),
        "braking_latency_ms":        ("spinBrakingLatency",        0), 
        # Obstacle & Safety
        # "obstacle_detection_buffer": ("spinObstacleBuffer",        2),
        # "sensitivity_threshold":     ("spinSensitivity",           2),
        # "collision_warning_ttc_s":   ("spinTTC",                   1),
        # Geometry
        # "vehicle_reference_width_m": ("spinVehicleWidth",          2),
        # "scale_factor_px_m":         ("spinScaleFactor",           2),
        # "camera_mounting_height_m":  ("spinCameraHeight",          2),
        # "look_ahead_distance_m":     ("spinLookAhead",             1),
    }
    for key, (attr, decimals) in mapping.items():
        if key in cfg:
            widget = getattr(win, attr, None)
            if widget:
                _set_val(widget, float(cfg[key]), decimals)


def reset_config_values(win) -> None:
    for name, (default, _step, decimals) in PARAM_CONFIG_MAIN.items():
        widget = getattr(win, name, None)
        if widget:
            _set_val(widget, default, decimals)


#  GET/SET/RESET  – Panel (Lane Detection & LKA)

def get_lane_lka_values(win) -> dict:
    return {
        # Lane Detection
        "point_density_ref":         _get_val(win.spinPointDensityRef),
        "curv_soft":                 _get_val(win.spinCurvSoft),
        "curv_hard":                 _get_val(win.spinCurvHard),
        # "curv_noise_gate":           _get_val(win.spinCurvNoiseGate),
        "k_head":                    _get_val(win.spinKHead),
        "offset_jump_thresh":        _get_val(win.spinOffsetJumpThresh),
        # "dx_noise_gate":             _get_val(win.spinDxNoiseGate),
        "k_lat":                     _get_val(win.spinKLat),
        "norm_conf_min":             _get_val(win.spinNormConfMin),
        # LKA Control
        "max_rate_deg_per_sec":      _get_val(win.spinMaxRateDeg),
        "deadzone_heading":          _get_val(win.spinDeadzoneHeading),
        "deadzone_lateral":          _get_val(win.spinDeadzoneLateral),
        # "steer_margin":              _get_val(win.spinSteerMargin),
        "max_lateral_error":         _get_val(win.spinMaxLateralError),
        "max_steer_abs":             _get_val(win.spinMaxSteerAbs),
        "safety_min_confidence":     _get_val(win.spinSafetyMinConf),
        "safety_max_steer_deg":      _get_val(win.spinSafetyMaxSteer),
        # ROI – Ego Lane
        "roi_ego_bl_x":        _get_val(win.spinRoiEgoBlX),
        "roi_ego_bl_y":        _get_val(win.spinRoiEgoBlY),
        "roi_ego_br_x":        _get_val(win.spinRoiEgoBrX),
        "roi_ego_br_y":        _get_val(win.spinRoiEgoBrY),
        "roi_ego_tl_x":        _get_val(win.spinRoiEgoTlX),
        "roi_ego_tl_y":        _get_val(win.spinRoiEgoTlY),
        "roi_ego_tr_x":        _get_val(win.spinRoiEgoTrX),
        "roi_ego_tr_y":        _get_val(win.spinRoiEgoTrY),
        # ROI – Danger Area
        "roi_danger_bl_x":     _get_val(win.spinRoiDangerBlX),
        "roi_danger_bl_y":     _get_val(win.spinRoiDangerBlY),
        "roi_danger_br_x":     _get_val(win.spinRoiDangerBrX),
        "roi_danger_br_y":     _get_val(win.spinRoiDangerBrY),
        "roi_danger_tl_x":     _get_val(win.spinRoiDangerTlX),
        "roi_danger_tl_y":     _get_val(win.spinRoiDangerTlY),
        "roi_danger_tr_x":     _get_val(win.spinRoiDangerTrX),
        "roi_danger_tr_y":     _get_val(win.spinRoiDangerTrY),
        # ROI – Warning Area
        "roi_warn_bl_x":       _get_val(win.spinRoiWarnBlX),
        "roi_warn_bl_y":       _get_val(win.spinRoiWarnBlY),
        "roi_warn_br_x":       _get_val(win.spinRoiWarnBrX),
        "roi_warn_br_y":       _get_val(win.spinRoiWarnBrY),
        "roi_warn_tl_x":       _get_val(win.spinRoiWarnTlX),
        "roi_warn_tl_y":       _get_val(win.spinRoiWarnTlY),
        "roi_warn_tr_x":       _get_val(win.spinRoiWarnTrX),
        "roi_warn_tr_y":       _get_val(win.spinRoiWarnTrY),
    }


def set_lane_lka_values(win, cfg: dict) -> None:
    mapping = {
        # Lane Detection
        "point_density_ref":         ("spinPointDensityRef",       0),
        "curv_soft":                 ("spinCurvSoft",              3),
        "curv_hard":                 ("spinCurvHard",              3),
        # "curv_noise_gate":           ("spinCurvNoiseGate",         3),
        "k_head":                    ("spinKHead",                 2),
        "offset_jump_thresh":        ("spinOffsetJumpThresh",      2),
        # "dx_noise_gate":             ("spinDxNoiseGate",           3),
        "k_lat":                     ("spinKLat",                  2),
        "norm_conf_min":             ("spinNormConfMin",           2),
        # LKA Control
        "max_rate_deg_per_sec":      ("spinMaxRateDeg",            1),
        "deadzone_heading":          ("spinDeadzoneHeading",       2),
        "deadzone_lateral":          ("spinDeadzoneLateral",       2),
        # "steer_margin":              ("spinSteerMargin",           2),
        "max_lateral_error":         ("spinMaxLateralError",       2),
        "max_steer_abs":             ("spinMaxSteerAbs",           1),
        "safety_min_confidence":     ("spinSafetyMinConf",         2),
        "safety_max_steer_deg":      ("spinSafetyMaxSteer",        1),
        # ROI – Ego Lane
        "roi_ego_bl_x":   ("spinRoiEgoBlX",  2), "roi_ego_bl_y":   ("spinRoiEgoBlY",  2),
        "roi_ego_br_x":   ("spinRoiEgoBrX",  2), "roi_ego_br_y":   ("spinRoiEgoBrY",  2),
        "roi_ego_tl_x":   ("spinRoiEgoTlX",  2), "roi_ego_tl_y":   ("spinRoiEgoTlY",  2),
        "roi_ego_tr_x":   ("spinRoiEgoTrX",  2), "roi_ego_tr_y":   ("spinRoiEgoTrY",  2),
        # ROI – Danger Area
        "roi_danger_bl_x": ("spinRoiDangerBlX", 2), "roi_danger_bl_y": ("spinRoiDangerBlY", 2),
        "roi_danger_br_x": ("spinRoiDangerBrX", 2), "roi_danger_br_y": ("spinRoiDangerBrY", 2),
        "roi_danger_tl_x": ("spinRoiDangerTlX", 2), "roi_danger_tl_y": ("spinRoiDangerTlY", 2),
        "roi_danger_tr_x": ("spinRoiDangerTrX", 2), "roi_danger_tr_y": ("spinRoiDangerTrY", 2),
        # ROI – Warning Area
        "roi_warn_bl_x":  ("spinRoiWarnBlX",  2), "roi_warn_bl_y":  ("spinRoiWarnBlY",  2),
        "roi_warn_br_x":  ("spinRoiWarnBrX",  2), "roi_warn_br_y":  ("spinRoiWarnBrY",  2),
        "roi_warn_tl_x":  ("spinRoiWarnTlX",  2), "roi_warn_tl_y":  ("spinRoiWarnTlY",  2),
        "roi_warn_tr_x":  ("spinRoiWarnTrX",  2), "roi_warn_tr_y":  ("spinRoiWarnTrY",  2),
    }
    for key, (attr, decimals) in mapping.items():
        if key in cfg:
            widget = getattr(win, attr, None)
            if widget:
                _set_val(widget, float(cfg[key]), decimals)


def reset_lane_lka_values(win) -> None:
    for name, (default, _step, decimals) in PARAM_CONFIG_LANE_LKA.items():
        widget = getattr(win, name, None)
        if widget:
            _set_val(widget, default, decimals)