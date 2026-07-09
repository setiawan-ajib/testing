from fins.udp import UDPFinsConnection
import struct
import fins

PLC_IP    = "192.168.250.1"
DEST_NODE = 1
SRC_NODE  = 100
DM        = fins.FinsPLCMemoryAreas().DATA_MEMORY_WORD

def try_connect():
    try:
        plc = UDPFinsConnection()
        plc.connect(PLC_IP, port=9600, bind_port=9601)
        plc.dest_node_add = DEST_NODE
        plc.srce_node_add = SRC_NODE
        print("Socket connected!")

        addr   = struct.pack(">HB", 0, 0)
        result = plc.memory_area_read(DM, addr, 1)
        print(f"   Raw result : {result!r}  (len={len(result) if result else 0})")

        # Parse hasil dengan aman
        if result and len(result) >= 2:
            value = struct.unpack(">H", result[:2])[0]
            print(f"   DM0 value  : {value}")
        elif result and len(result) == 1:
            value = result[0]
            print(f"   DM0 value  : {value}  (1 byte)")
        else:
            print("   DM0 value  : (empty response — DM0 mungkin = 0)")

        print(f"   IP        : {PLC_IP}")
        print(f"   Dest Node : {DEST_NODE}")
        print(f"   Src Node  : {SRC_NODE}")
        return plc

    except Exception as e:
        print(f"Failed: {e}")
        import traceback; traceback.print_exc()
        return None

if __name__ == "__main__":
    plc = try_connect()
    if plc:
        print("\n>>> PLC siap digunakan.")
    else:
        print("\n>>> Cek kabel / IP / node address PLC.")