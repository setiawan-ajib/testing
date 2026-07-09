import struct
import traceback
from fins.udp import UDPFinsConnection
import fins
# from plc_omron.test_connection import try_connect

class UIFINSForwarder:
    PLC_IP    = "192.168.250.1"
    DEST_NODE = 1
    SRCE_NODE  = 100

    PARAM_WORD_MAP = {
        "Kp":                     20,
        "Ki":                     22,
        "Kd":                     24,
        "Correction Limit":       26,
        "Steering Center Offset": 28,
        "Brake Delay":            30,
    }

    def __init__(self):
        self.plc = None
        self.connect()

    def connect(self):
        try:
            self.plc = UDPFinsConnection()
            self.plc.connect(self.PLC_IP, port=9600, bind_port=9601)  # ← bind_port beda
            self.plc.dest_node_add = self.DEST_NODE
            self.plc.srce_node_add = self.SRCE_NODE
            print(f"[UIFINSForwarder] Connected to PLC {self.PLC_IP}:9600 (bind_port=9601).")
        except OSError as e:
            print(
                f"[UIFINSForwarder] CONNECT FAILED (OSError) — "
                f"PLC IP may be unreachable or port already in use: {e}"
            )
            self.plc = None
        except Exception as e:
            print(f"[UIFINSForwarder] CONNECT FAILED ({type(e).__name__}): {e}")
            print(traceback.format_exc())
            self.plc = None

    def _close_socket(self):
        try:
            if self.plc and hasattr(self.plc, "fins_socket"):
                self.plc.fins_socket.close()
                print("[UIFINSForwarder] Socket closed.")
        except Exception as e:
            print(f"[UIFINSForwarder] Socket close error ({type(e).__name__}): {e}")
        finally:
            self.plc = None

    def disconnect(self):
        self._close_socket()
        print("[UIFINSForwarder] Disconnected from PLC.")

    def ensure_connection(self):
        if self.plc is None:
            print("[UIFINSForwarder] ensure_connection: plc is None, attempting reconnect...")
            self.connect()
            return
        try:
            self._read_dm_word(0)
        except Exception as e:
            print(f"[UIFINSForwarder] ensure_connection: ping DM0 FAILED ({type(e).__name__}): {e}")
            print("[UIFINSForwarder] Connection lost, reconnecting...")
            self._close_socket()
            self.connect()

    def _dm_address_bytes(self, word: int) -> bytes:
        return struct.pack(">HB", word, 0)

    def write_word(self, word: int, value: int):
        if self.plc is None:
            raise ConnectionError("[UIFINSForwarder] write_word: PLC not connected.")
        addr  = self._dm_address_bytes(word)
        data  = struct.pack(">H", value & 0xFFFF)
        self.plc.memory_area_write(
            fins.FinsPLCMemoryAreas().DATA_MEMORY_WORD,
            addr,
            data,
            1
        )

    def _read_dm_word(self, word: int) -> int:
        if self.plc is None:
            raise ConnectionError(f"[UIFINSForwarder] _read_dm_word(DM{word}): PLC not connected.")
        addr   = self._dm_address_bytes(word)
        result = self.plc.memory_area_read(
            fins.FinsPLCMemoryAreas().DATA_MEMORY_WORD,
            addr,
            1
        )
        if not result or len(result) < 2:
            raise ValueError(
                f"[UIFINSForwarder] _read_dm_word(DM{word}): "
                f"Invalid response from PLC: {result!r}"
            )
        return struct.unpack(">H", result[-2:])[0]

    def send_ui_params(self, ui_data: dict):
        self.ensure_connection()
        if self.plc is None:
            raise ConnectionError("[UIFINSForwarder] send_ui_params: PLC not available after reconnect.")

        SEND_MAP = {
            "Kp":                     (20, 100),
            "Ki":                     (22, 100),
            "Kd":                     (24, 100),
            "Correction Limit":       (26, 100),
            "Steering Center Offset": (28, 100),
            "Brake Delay":            (30, 1),
        }

        print("[UIFINSForwarder] send_ui_params: Sending parameters to PLC...")
        for param, (word, scale) in SEND_MAP.items():
            raw_val = ui_data.get(param, 0)
            int_val = int(round(float(raw_val) * scale)) & 0xFFFF
            try:
                self.write_word(word, int_val)
                print(
                    f"[UIFINSForwarder] WRITE DM{word} <- {int_val}  "
                    f"({param}, raw={raw_val}, x{scale})"
                )
            except Exception as e:
                print(
                    f"[UIFINSForwarder] WRITE FAILED DM{word} ({param}): "
                    f"{type(e).__name__}: {e}"
                )
                raise

        print("[UIFINSForwarder] send_ui_params: All parameters sent to PLC successfully.")

    def read_ui_params(self) -> dict | None:
        print("[UIFINSForwarder] read_ui_params: Attempting to read from PLC...")
        self.ensure_connection()
        if self.plc is None:
            print(
                "[UIFINSForwarder] read_ui_params: SKIPPED — "
                "PLC not available after ensure_connection()."
            )
            return None

        READ_MAP = {
            "steering_responsiveness": (20, 100),
            "steady_state_correction": (22, 100),
            "damping_stability":       (24, 100),
            "correction_limit":        (26, 100),
            "steering_center_offset":  (28, 100),
            "braking_latency_ms":      (30, 1),
        }

        result = {}
        try:
            for key, (word, scale) in READ_MAP.items():
                raw = self._read_dm_word(word)
                value = raw / scale
                result[key] = value
                print(
                    f"[UIFINSForwarder] READ DM{word}: "
                    f"raw={raw}, scale=/{scale}, value={value} ({key})"
                )

            print(f"[UIFINSForwarder] read_ui_params: SUCCESS. Result: {result}")
            return result

        except ConnectionError as e:
            print(f"[UIFINSForwarder] read_ui_params: CONNECTION ERROR: {e}")
            return None
        except ValueError as e:
            print(f"[UIFINSForwarder] read_ui_params: VALUE ERROR (invalid PLC response): {e}")
            return None
        except Exception as e:
            print(
                f"[UIFINSForwarder] read_ui_params: UNEXPECTED ERROR "
                f"({type(e).__name__}): {e}"
            )
            print(traceback.format_exc())
            return None