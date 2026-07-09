import time
import math
from plc_omron.fins_steering_check import SteeringMonitor

def clamp(val, vmin, vmax):
    return max(vmin, min(vmax, val))

class SafetyLKA:
    def __init__(self, steering_monitor: SteeringMonitor):
        self.MAX_STEER_RATE = 800
        self.TIMEOUT_SEC = 0.25
        self.MIN_ENABLE_HOLD = 0.5
        self.STEER_POS_MIN = -350
        self.STEER_POS_MAX = 350
        self.POS_SCALE = 0.01
        self.MAX_TRACK_ERROR = 1.0
        self.ERROR_CODE = -999
        self.MIN_CONFIDENCE = 0.70
        self.MAX_STEER_DEG = 3.0
        self.prev_cmd = 0.0
        self.prev_ts = time.time()
        self.enable_latch = False
        self.last_enable_ts = 0.0

        #self.steering = steering_monitor

    def update(self, lka_out, cfg=None):
        if cfg:
            min_conf    = cfg.get("safety_min_confidence", self.MIN_CONFIDENCE)
            max_steer   = cfg.get("safety_max_steer_deg",  self.MAX_STEER_DEG)
            steer_rate  = cfg.get("max_rate_deg_per_sec", self.MAX_STEER_RATE)
        else:
            min_conf    = self.MIN_CONFIDENCE
            max_steer   = self.MAX_STEER_DEG
            steer_rate  = self.MAX_STEER_RATE

        now = time.time()

        if lka_out is None:
            return self._safe_stop("NULL_INPUT")
        """
        # ===============================
        # STEERING FEEDBACK (PLC)
        # ===============================
        try:
            fb = self.steering.get_feedback()
        except Exception:
            return self._safe_stop("STEER_FB_READ_FAIL")

        if fb is None:
            return self._safe_stop("STEER_FB_INVALID")

        # HARD FAULT dari PLC
        if fb.get("error", True):
            return self._safe_stop("STEER_HW_FAULT")

        pos = fb.get("position", None)
        if not isinstance(pos, int):
            return self._safe_stop("STEER_POS_INVALID")

        # Range plausibility
        if pos < self.STEER_POS_MIN or pos > self.STEER_POS_MAX:
            return self._safe_stop("STEER_POS_OUT_OF_RANGE")

        actual_deg = pos * self.POS_SCALE
        """
        
        if "timestamp" not in lka_out:
            return self._safe_stop("NO_TIMESTAMP")
        
        ts = lka_out.get("timestamp", 0)
        if now - ts > self.TIMEOUT_SEC:
            return self._safe_stop("LKA_TIMEOUT")

        confidence = lka_out.get("confidence", 0.0)
        if confidence < min_conf:
            return self._safe_stop("LOW_CONFIDENCE")

        enable = lka_out.get("enable", False)

        if enable and not self.enable_latch:
            self.enable_latch = True
            self.last_enable_ts = now

        if not enable:
            if now - self.last_enable_ts > self.MIN_ENABLE_HOLD:
                self.enable_latch = False

        if self.enable_latch:
            if now - self.last_enable_ts < self.MIN_ENABLE_HOLD:
                return self._safe_stop("ENABLE_HOLD")

        if not self.enable_latch:
            return self._safe_stop("LKA_DISABLED")

        cmd = lka_out.get("heading_error", 0.0)

        if not isinstance(cmd, (int, float)):
            return self._safe_stop("INVALID_CMD")
        
        if not math.isfinite(cmd):
            return self._safe_stop("CMD_NOT_FINITE")

        cmd = clamp(cmd, -max_steer, max_steer)

        dt = clamp(now - self.prev_ts, 0.01, 0.2)
        max_delta = steer_rate * dt
        delta = clamp(cmd - self.prev_cmd, -max_delta, max_delta)
        safe_cmd = self.prev_cmd + delta

        # ===============================
        # TRACKING CHECK (RUNAWAY PROTECTION)
        # ===============================
        #if abs(actual_deg - self.prev_cmd) > self.MAX_TRACK_ERROR:
        #    return self._safe_stop("STEER_NOT_TRACKING")

        self.prev_cmd = safe_cmd
        self.prev_ts = now

        return {
            "valid": True,
            "steering_cmd_deg": safe_cmd,
            "reason": "OK"
        }

    def _safe_stop(self, reason):
        # self.prev_cmd = 0.0
        self.prev_ts = time.time()

        return {
            "valid": False,
            "steering_cmd_deg": self.ERROR_CODE,
            "reason": reason
        }
