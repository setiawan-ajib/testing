from plc_omron.fins_interface import FINSInterface

class SteeringMonitor:
    def __init__(self, plc: FINSInterface):
        self.plc = plc

    def read_position(self) -> int:
        try:
            return self.plc.read_register_int("D17")
        except Exception as e:
            print(f"[SteeringMonitor] Read position failed, reconnecting: {e}")
            self.plc.reconnect()
            return self.plc.read_register_int("D17")

    def read_error(self) -> bool:
        try:
            return self.plc.read_bit("M01")
        except Exception as e:
            print(f"[SteeringMonitor] Read error failed, reconnecting: {e}")
            self.plc.reconnect()
            return self.plc.read_bit("M01")

    def get_feedback(self) -> dict:
        return {
            "position": self.read_position(),
            "error": self.read_error(),
        }