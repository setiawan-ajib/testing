import time
import struct
import fins
from fins.udp import UDPFinsConnection

class FINSInterface:
    def __init__(
        self,
        plc_ip: str = "192.168.250.1",
        dest_node: int = 1, #PLC node number
        srce_node: int = 100, #Jetson/PC node number
        port: int = 9600,
        bind_port: int = 9602,
        heartbeat_interval: float = 1.0
    ):
        
        # self.plc = UDPFinsConnection()
        self.plc_ip = plc_ip
        self.dest_node = dest_node
        self.srce_node = srce_node
        self.port = port
        self.bind_port = bind_port
        self.heartbeat_interval = heartbeat_interval

        self.last_brake_cmd = None
        self.last_heartbeat_time = 0.0
        self.heartbeat_state = 0
        self._DM = fins.FinsPLCMemoryAreas().DATA_MEMORY_WORD
        self._MR = fins.FinsPLCMemoryAreas().CIO_WORD

        self.plc = None
        self.connect()
    
    
    def connect(self):
        try:
            self.plc = UDPFinsConnection()
            self.plc.connect(self.plc_ip, port=self.port, bind_port=self.bind_port)
            self.plc.dest_node_add = self.dest_node
            self.plc.srce_node_add = self.srce_node
            print(f"[FINSInterface] Connected to PLC {self.plc_ip}")
        except Exception as e:
            print(f"[FINSInterface] Connect failed: {e}")
            self.plc = None

    def _close_socket(self):
        try:
            if self.plc and hasattr(self.plc, "fins_socket"):
                self.plc.fins_socket.close()
        except Exception as e:
            print(f"[FINSInterface] Socket close error: {e}")
        finally:
            self.plc = None

    def ensure_connection(self):
        if self.plc is None:
            self.connect()
            return
        try:
            self._read_dm_word(0)   # ping: baca DM0
        except Exception:
            print("[FINSInterface] Connection lost, reconnecting...")
            self.reconnect()
    
    def reconnect(self):
        print("[FINSInterface] Reconnecting...")
        self._close_socket()
        time.sleep(0.5)
        self.connect()

    def _dm_address(self, word: int) -> bytes:
        return struct.pack(">HB", word, 0)

    def _read_dm_word(self, word: int) -> int:
        addr = self._dm_address(word)
        result = self.plc.memory_area_read(self._DM, addr, 1)
        if not result or len(result) < 2:
            raise ValueError(f"[FINSInterface] Invalid response for DM{word}: {result!r}")
        return struct.unpack(">H", result[:2])[0]

    def _write_dm_word(self, word: int, value: int):
        addr = self._dm_address(word)
        data = struct.pack(">H", value & 0xFFFF)
        self.plc.memory_area_write(self._DM, addr, data, 1)

    def _write_bit_word(self, word: int, value: bool):
        addr = self._dm_address(word)
        data = struct.pack(">H", int(value))
        self.plc.memory_area_write(self._MR, addr, data, 1)


    def _read_dm_word_signed(self, word: int) -> int:
        addr = self._dm_address(word)
        result = self.plc.memory_area_read(self._DM, addr, 1)
        if not result or len(result) < 2:
            raise ValueError(f"[FINSInterface] Invalid response for DM{word}: {result!r}")
        return struct.unpack(">h", result[:2])[0]

    def _write_cio_bit(self, word: int, bit: int, value: bool):
        addr = struct.pack(">HB", word, bit)
        data = b'\x01' if value else b'\x00'
        self.plc.memory_area_write(self._MR, addr, data, 1)
    
    def _read_bit_word(self, word: int, bit: int) -> bool:
        addr = struct.pack(">HB", word, bit)
        result = self.plc.memory_area_read(self._MR, addr, 1)
        if result:
            return result[0] != 0
        return False

    def safe_write(self, func, *args, **kwargs):
        try:
            self.ensure_connection()
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[FINSInterface] Write failed, retrying: {e}")
            self.reconnect()
            try:        
                return func(*args, **kwargs)
            except Exception as e2:
                print(f"[FINSInterface] Retry also failed: {e2}")
                return None   
            
    def update(self, safety_output: dict):
        brake_cmd = int(safety_output.get("brake", 0))
        self._send_brake_cmd(brake_cmd)
        self._update_heartbeat()

    def _send_brake_cmd(self, brake_cmd: int):
        if brake_cmd == self.last_brake_cmd:
            return
        self.safe_write(self._write_dm_word, 10, brake_cmd)
        self.last_brake_cmd = brake_cmd

    def _update_heartbeat(self):
        now = time.time()
        # print(now)
        if now - self.last_heartbeat_time >= self.heartbeat_interval:
            self.heartbeat_state ^= 1
            # write heartbeat ke DM10 bit 0 — encode sebagai word (0 / 1)
            self.safe_write(self._write_bit_word, 10, self.heartbeat_state)
            self.last_heartbeat_time = now

    def read_brake_error(self) -> bool:
        try:
            return self._read_bit_word(2, 0)
        except Exception as e:
            print(f"[FINSInterface] read_brake_error failed: {e}")
            raise

    def read_emergency_stop(self) -> bool:
        try:
            return self._read_bit_word(0, 0)
        except Exception as e:
            print(f"[FINSInterface] read_emergency_stop failed: {e}")
            raise

    def trigger_buzzer(self, on: bool):
        self.safe_write(self._write_bit_word, 12, int(on))

    def update_camera_status(self, is_active: bool):
        self.safe_write(self._write_bit_word, 13, int(is_active))
        print(f"[FINSInterface] Camera status → M13 = {int(is_active)} ({'ON' if is_active else 'OFF'})")

    def update_steering(self, lka_output: dict, max_rate_deg_per_sec: float):
        steering_active = int(lka_output.get("enable", 0))
        # M11: active / release — tulis ke word 15 area CIO
        self.safe_write(self._write_bit_word, 15, steering_active)

        # D11: angle deg
        angle_deg = int(float(lka_output.get("heading_error", 0.0))*100)
        # angle_deg = float(lka_output.get("heading_error", 0.0)) #hilangkan 100 / ubah plc
        self.safe_write(self._write_dm_word, 11, angle_deg) 

        # D13: rate limit deg/s
        self.safe_write(self._write_dm_word, 13, int(max_rate_deg_per_sec))

        # D15-D16: alive counter (32-bit → 2 words)
        if not hasattr(self, "_steering_counter"):
            self._steering_counter = 0

        self._steering_counter = (self._steering_counter + 1) % 0x10000
        self.safe_write(self._write_dm_word, 15, self._steering_counter)
    
    def read_register_int(self, reg: str) -> int:
        #read DM dari area D
        if reg.startswith("D"):
            word = int(reg[1:])
            return self._read_dm_word_signed(word)
        raise ValueError(f"[FINSInterface] Format register tidak dikenal: {reg}")

    def read_bit(self, address: str) -> bool:
        #read bit dari area M
        if address.startswith("M"):
            parts = address[1:].split(".")
            word = int(parts[0])
            bit = int(parts[1]) if len(parts) > 1 else 0
            return self._read_bit_word(word, bit)
        raise ValueError(f"[FINSInterface] Format address tidak dikenal: {address}")
    
    
    # def monitor_m17(self, poll_interval: float = 0.1):

    #     import subprocess

    #     print("[FINSInterface] Mulai monitoring M17...")
    #     previous_state = None

    #     while True:
    #         try:
    #             self.ensure_connection()
    #             current_state = self._read_bit_word(17, 0)

    #             if previous_state is None:
    #                 print(f"[FINSInterface] M17 initial state = {int(current_state)}")
    #                 previous_state = current_state

    #             elif current_state != previous_state:
    #                 if not current_state and previous_state:
    #                     # 1 → 0
    #                     print("[FINSInterface] M17: 1 → 0 | Jetson OFF")
    #                     subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
    #                 elif current_state and not previous_state:
    #                     # 0 → 1
    #                     print("[FINSInterface] M17: 0 → 1 | Jetson ON")

    #                 previous_state = current_state

    #         except Exception as e:
    #             print(f"[FINSInterface] monitor_m17 error: {e}")
    #             self.reconnect()

    #         time.sleep(poll_interval)
    
    
    def read_ignition_status(self) -> bool:
        try:
            addr = struct.pack(">HB", 17, 0)
            result = self.plc.memory_area_read(self._MR, addr, 1)
            if not result or len(result) < 2:
                raise ValueError(f"Invalid response CIO17: {result!r}")
            val = struct.unpack('>H', result[-2:])[0]
            print(f"[FINSInterface] CIO17 raw word = {val}")
            return val  # kembalikan nilai mentah
        except Exception as e:
            print(f"[FINSInterface] read_ignition_status failed: {e}")
            raise