import time
import math
import random

from fusion_layer.ego_lane_estimation import estimate_ego_lane_data
from fusion_layer.normalize_ego_lane import normalize_ego_lane
from decision_layer.lka import lane_keeping_assist
from safety_layer.safety_lka import SafetyLKA

# DUMMY STEERING MONITOR
class DummySteeringMonitor:
    def get_feedback(self):
        # return selalu valid
        return {"position": 0, "error": False}

# DUMMY LANE GENERATOR
def generate_dummy_lanes(
    frame_width,
    frame_height,
    mode="straight",
    noise_px=2.0,
    drop_prob=0.0
):
    """
    mode:
      - straight
      - left_curve
      - right_curve
      - one_side_missing
      - lost
    """

    lanes_points = [[], [], [], []]
    lanes_detected = [False, False, False, False]

    if random.random() < drop_prob:
        return lanes_points, lanes_detected

    y_vals = list(range(int(frame_height * 0.5), frame_height, 10))

    lane_width_px = frame_width * 0.25
    center_x = frame_width / 2

    for y in y_vals:
        curve = 0.0
        if mode == "left_curve":
            curve = -0.0008 * (y - frame_height * 0.6) ** 2
        elif mode == "right_curve":
            curve = 0.0008 * (y - frame_height * 0.6) ** 2

        noise = random.uniform(-noise_px, noise_px)

        left_x = center_x - lane_width_px / 2 + curve + noise
        right_x = center_x + lane_width_px / 2 + curve + noise

        lanes_points[1].append((left_x, y))
        lanes_points[2].append((right_x, y))

    lanes_detected[1] = True
    lanes_detected[2] = True

    if mode == "one_side_missing":
        lanes_points[2] = []
        lanes_detected[2] = False

    if mode == "lost":
        lanes_points = [[], [], [], []]
        lanes_detected = [False] * 4

    return lanes_points, lanes_detected


# MAIN TEST LOOP
def run_dummy_test():
    frame_width = 1280
    frame_height = 720

    lka_state = {}
    safety_lka = SafetyLKA(steering_monitor=DummySteeringMonitor())

    test_sequence = [
        ("straight", 50),
        ("right_curve", 50),
        ("left_curve", 50),
        ("one_side_missing", 30),
        ("lost", 30),
        ("straight", 50),
    ]

    frame_id = 0

    print("Starting Dummy LKA Test...\n")

    for mode, frames in test_sequence:
        print(f"\n=== MODE: {mode.upper()} ===")

        for _ in range(frames):
            frame_id += 1

            lanes_points, lanes_detected = generate_dummy_lanes(
                frame_width,
                frame_height,
                mode=mode,
                noise_px=3.0,
                drop_prob=0.05
            )

            ego_lane_data = estimate_ego_lane_data(
                lanes_points,
                lanes_detected,
                frame_width,
                frame_height
            )

            ego_lane_norm = normalize_ego_lane(
                lanes_points,
                lanes_detected,
                frame_width,
                frame_height,
                confidence=ego_lane_data["confidence"]
            )

            if ego_lane_norm:
                lka_out = lane_keeping_assist(
                    ego_lane_norm,
                    frame_id,
                    prev_state=lka_state
                )
            else:
                lka_out = None

            if not lka_out or lka_out.get("reset", False):
                lka_state.clear()
            elif lka_out.get("enable", False):
                lka_state.update(lka_out)

            safe_out = safety_lka.update(lka_out)

            print(
                f"F:{frame_id:04d} | "
                f"conf={ego_lane_data['confidence']:.2f} | "
                f"valid={safe_out['valid']} | "
                f"steer={safe_out['steering_cmd_deg']:.2f} | "
                f"reason={safe_out['reason']}"
            )

            time.sleep(0.03)  # ~30 FPS

    print("\nDummy LKA Test Finished.")


if __name__ == "__main__":
    run_dummy_test()
