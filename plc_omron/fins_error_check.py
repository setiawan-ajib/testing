import time
import threading
from plc_omron.fins_interface import FINSInterface


class BrakeErrorMonitor:
    def __init__(
        self,
        plc: FINSInterface,
        check_interval: float = 0.1,
        debounce_frames: int = 3,
        plc_timeout: float = 2.0,
    ):
        self.plc = plc
        self.check_interval = check_interval
        self.debounce_frames = debounce_frames
        self.plc_timeout = plc_timeout
        self._running = False
        self._thread = None
        self._prev_error = None
        self._stable_count = 0
        self._last_plc_ok = time.time()
        self._last_reported = None

    def start(self, callback=None):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, args=(callback,), daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _run_loop(self, callback):
        while self._running:
            try:
                self.plc.ensure_connection()
                
                brake_error = self.plc.read_brake_error()
                emergency_stop = self.plc.read_emergency_stop()
                error_state = brake_error or emergency_stop

                # Debounce: hitung frame stabil
                if error_state == self._prev_error:
                    self._stable_count += 1
                else:
                    self._stable_count = 1

                if self._stable_count >= self.debounce_frames:
                    if error_state != self._last_reported:
                        print(f"[BrakeErrorMonitor] State changed → error={error_state}")
                    if callback:
                        callback(error_state)
                    self._last_reported = error_state
                self._prev_error = error_state
                

            except Exception as e:
                print(f"[BrakeErrorMonitor] Error membaca PLC: {e}")
                if time.time() - self._last_plc_ok > self.plc_timeout:
                    print("[BrakeErrorMonitor] PLC Timeout")
                    if callback:
                        callback(True)

            time.sleep(self.check_interval)