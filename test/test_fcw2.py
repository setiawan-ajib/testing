import time
from decision_layer.fcw import FCW
from safety_layer.safety_fcw import SafetyFCWBinary

# ===== Inisialisasi sistem =====
fcw_system = FCW(iou_threshold=0.5, alpha=0.5)
safety_fcw = SafetyFCWBinary(
    conf_min=0.7,
    ttc_hard=0.8,
    stable_frames=3,
    latch_time=1.0
)

# ===== Dummy object =====
ego_lane_target = {
    "bbox": [500, 400, 600, 500], 
    "confidence": 0.9, 
    "track_id": 1, 
    "class": "car"
}
stable_objects = [ego_lane_target.copy()]

# ===== Sequence dinamis: kecepatan & TTC =====
# TTC awal (detik) OFF → LOW → MEDIUM → HARD → MEDIUM → LOW → OFF
ttc_sequence_off_on_off = [
    float('inf'), float('inf'), float('inf'), float('inf'), float('inf'),  # OFF
    4.5, 4.0, 3.5, 3.0, 2.5,  # LOW
    1.5, 1.2, 1.0, 1.5, 1.3, #MEDIUM
    1.5, 1.2, 1.0, 0.8, 0.7, 0.6, 0.5, 0.5, 0.5, 0.6, 0.7, 0.8,  # HARD diperpanjang
    1.0, 1.2, 1.5, #MEDIUM
    None, None, None, None, None, None,
    2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,  # LOW
    float('inf'), float('inf'), float('inf'), float('inf'), float('inf')  # OFF
]

# Asumsi kendaraan ego speed (m/s)
ego_speed = 15.0  # 54 km/h
target_speed_sequence = [
    0.0 if ttc==float('inf') else 10.0 for ttc in ttc_sequence_off_on_off
]

# ===== Fungsi hitung TTC dinamis =====
def compute_ttc(distance, v_ego, v_target):
    relative_speed = v_ego - v_target
    if relative_speed <= 0:
        return float('inf')
    return distance / relative_speed

# ===== Posisi awal objek (x1,y1,x2,y2) =====
obj_y = 400
obj_height = 100
obj_width = 100

print("=== TEST FCW + SAFETY FCW LEVELS (DYNAMIC OBJECT) ===")

for frame, (ttc_approx, target_speed) in enumerate(zip(ttc_sequence_off_on_off, target_speed_sequence)):
    print(f"\nFrame {frame+1}")

    # Distance proxy = TTC * relative_speed (estimasi)
    if ttc_approx is None:
        distance = 50
    elif ttc_approx == float('inf'):
        distance = 100.0
    else:
        distance = ttc_approx * max(ego_speed - target_speed, 0.1)

    # Simulasikan objek bergerak maju (y axis)
    obj_y += target_speed * 0.2  # 0.2s per frame
    ego_lane_target["bbox"] = [500, int(obj_y), 500 + obj_width, int(obj_y) + obj_height]
    stable_objects[0] = ego_lane_target.copy()
    danger_vehicle = None

    # ===== Jalankan FCW =====
    fcw_packet = fcw_system.run(danger_vehicle, ego_lane_target, stable_objects, target_obj=ego_lane_target)
    if ttc_approx is None:
        fcw_packet['ttc_proxy'] = None
        fcw_packet['level'] = 'DANGER'
        fcw_packet['fcw_active'] = True
    else:
        # Override TTC dinamis
        fcw_packet['ttc_proxy'] = compute_ttc(distance, ego_speed, target_speed)

        # Tentukan level FCW berdasarkan TTC dinamis
        ttc_val = fcw_packet['ttc_proxy']
        if ttc_val == float('inf'):
            fcw_packet['level'] = 'OFF'
            fcw_packet['fcw_active'] = False
        elif ttc_val < 0.8:
            fcw_packet['level'] = 'HARD'
            fcw_packet['fcw_active'] = True
        elif ttc_val < 1.5:
            fcw_packet['level'] = 'MEDIUM'
            fcw_packet['fcw_active'] = True
        elif ttc_val < 2.5:
            fcw_packet['level'] = 'LOW'
            fcw_packet['fcw_active'] = True
        else:
            fcw_packet['level'] = 'OFF'
            fcw_packet['fcw_active'] = False

    print("FCW output:", fcw_packet)

    # ===== Jalankan SafetyFCW =====
    safety_result = safety_fcw.update(fcw_packet)
    print("SafetyFCW output:", safety_result)

    time.sleep(0.2)  # simulasi delay frame