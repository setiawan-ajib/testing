import time
from collections import deque
import math
class SafetyFCWBinary:
    def __init__(
        self,
        conf_min=0.7,      # minimal confidence untuk valid brake
        ttc_hard=0.8,      # manusia 0.6
        stable_frames=5,   # jumlah frame harus stabil sebelum brake ON
        latch_time=0.5     # minimal brake ON (detik)
    ):
        # parameter filter
        self.conf_min = conf_min
        self.ttc_hard = ttc_hard
        self.stable_frames = stable_frames
        self.latch_time = latch_time

        # state internal
        self.state = "IDLE"      # IDLE | ARMED | BRAKING
        self.hard_counter = 0
        self.ttc_history = deque(maxlen=stable_frames)
        self.danger_counter = 0
        self.danger_history = deque(maxlen=stable_frames)
        self.warning_counter = 0
        self.warning_history = deque(maxlen=stable_frames)
        self.brake_on_time = None

    def _now(self):
        return time.monotonic()

    def update(self, fcw_packet):
        output = {"brake": 0, "reason": "SAFE_DEFAULT"}

        if fcw_packet is None or not fcw_packet.get("fcw_active", False):
            self._reset("NO_FCW_RISK")
            return output

        conf = fcw_packet.get("confidence", 1.0)
        stable_conf = fcw_packet.get("stable_conf", True)
        level = fcw_packet.get("level", "OFF")
        ttc = fcw_packet.get("ttc_proxy", None)

        # --- CONFIDENCE & LEVEL CHECK ---
        if conf < self.conf_min or not stable_conf:
            self._reset("LOW_CONF")
            return output

        if level not in ["DANGER", "HARD", "WARNING"]:
            self._reset("NOT_DANGER/HARD/WARNING")
            return output

        # --- DANGER LEVEL SPECIAL HANDLING ---
        if level == "DANGER":
            self.danger_history.append(1.0)
            self.danger_counter += 1
            if self.danger_counter >= self.stable_frames:
                now = self._now()
                if self.state != "BRAKING":
                    self.state = "BRAKING"
                    self.brake_on_time = now
                    return {"brake": 2, "reason": "BRAKE_FULL_DANGER"}
                else:
                    if now - self.brake_on_time < self.latch_time:
                        return {"brake": 2, "reason": "BRAKE_LATCH_DANGER"}
                    return {"brake": 2, "reason": "BRAKE_HOLD_DANGER"}
            else:
                return {"brake":0, "reason":"WAIT_STABLE_DANGER"}
        
        # --- WARNING LEVEL SPECIAL HANDLING ---
        if level == "WARNING":
            self.warning_history.append(1.0)
            self.warning_counter += 1
            if self.warning_counter >= self.stable_frames:
                now = self._now()
                if self.state != "BRAKING":
                    self.state = "BRAKING"
                    self.brake_on_time = now
                    return {"brake": 1, "reason": "BRAKE_HALF_WARNING"}
                else:
                    if now - self.brake_on_time < self.latch_time:
                        return {"brake": 1, "reason": "BRAKE_LATCH_WARNING"}
                    return {"brake": 1, "reason": "BRAKE_HOLD_WARNING"}
            else:
                return {"brake":0, "reason":"WAIT_STABLE_WARNING"}

        # --- TTC CHECK ---
        if not isinstance(ttc, (int, float)) or math.isnan(ttc):
            self._reset("BAD_TTC")
            return output

        if ttc > self.ttc_hard:
            self._reset("TTC_TOO_HIGH")
            return output

        # --- STABILITY CHECK ---
        self.ttc_history.append(ttc)
        if len(self.ttc_history) < self.stable_frames:
            return {"brake": 0, "reason": "WAIT_STABLE"}

        if max(self.ttc_history) - min(self.ttc_history) > 0.3:
            self._reset("TTC_UNSTABLE")
            return output

        # --- STATE MACHINE ---
        now = self._now()
        if self.state in ["IDLE", "ARMED"]:
            self.hard_counter += 1
            if self.hard_counter >= self.stable_frames:
                self.state = "BRAKING"
                self.brake_on_time = now
                return {"brake": 1, "reason": "BRAKE_ON_HALF"}

        if self.state == "BRAKING":
            if now - self.brake_on_time < self.latch_time:
                return {"brake": 1, "reason": "BRAKE_LATCH"}

            if ttc > self.ttc_hard or conf < (self.conf_min - 0.2):
                self._reset("BRAKE_RELEASE")
                return {"brake": 0, "reason": "BRAKE_RELEASE"}

            return {"brake": 1, "reason": "BRAKE_HOLD"}

        return output

    def _reset(self, reason):
        self.state = "IDLE"
        self.hard_counter = 0
        self.danger_counter = 0
        self.ttc_history.clear()
        self.danger_history.clear()
        self.brake_on_time = None
        self.warning_counter = 0
