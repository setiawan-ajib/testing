import argparse
import os
import sys
import threading
import queue
from pathlib import Path
import torch
from ultralytics.utils.plotting import Annotator, colors
from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (
    check_file,
    check_img_size,
    check_imshow,
    check_requirements,
    non_max_suppression,
    scale_boxes,
    strip_optimizer,
)
from utils.torch_utils import select_device, smart_inference_mode
from yolo.tracking_pipeline import TrackingPipeline
from yolo.target_vehicle_selector import get_ego_lane_roi, get_danger_area_roi, get_warning_area_roi
import cv2
import time
from lane_detection.ultrafast_lane_detector.ultrafast_lane_detector import UltrafastLaneDetector
# from line_detection_ufld.ultrafastLaneDetector.ultrafastLaneDetector import UltrafastLaneDetector
from lane_detection.ultrafast_lane_detector.temporal_smoothing import TemporalLaneSmoother
# from line_detection_ufld.ultrafastLaneDetector.temporal_smoothing import TemporalLaneSmoother
from decision_layer.fcw import FCW
from fusion_layer.ego_lane_estimation import estimate_ego_lane_data
from fusion_layer.normalize_ego_lane import normalize_ego_lane
from decision_layer.lka import lane_keeping_assist
from safety_layer.safety_fcw import SafetyFCWBinary
from safety_layer.safety_lka import SafetyLKA
from argparse import Namespace
from plc_omron.fins_interface import FINSInterface
from plc_omron.fins_error_check import BrakeErrorMonitor
from plc_omron.fins_steering_check import SteeringMonitor
from ui.output_ui import ADASUI
from config import shared_config

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))

lane_colors = [
    (0, 0, 255),    # lane 0 – merah
    (0, 255, 0),    # lane 1 – hijau
    (255, 0, 0),    # lane 2 – biru
    (0, 255, 255)   # lane 3 – kuning
]

INFER_EVERY_N_FRAMES = 2 # N -> ubah 2 atau 1
IGNITION_CHECK_INTERVAL = 5  # detik; set 0 buat disable cek m17
lane_frame_id = 0
lane_cache    = None

lka_state = {
    "enable": False,
    "heading_error": 0.0
}

show_ego_lane_roi = True

DISPLAY_W = 1024
DISPLAY_H = 535

WARNING_LOGO     = cv2.imread("assets/data/pictures/warning.png", cv2.IMREAD_UNCHANGED)
STEER_LEFT_ICON  = cv2.imread("assets/data/pictures/left.png",    cv2.IMREAD_UNCHANGED)
STEER_RIGHT_ICON = cv2.imread("assets/data/pictures/right.png",   cv2.IMREAD_UNCHANGED)
SETTING_ICON     = cv2.imread("assets/data/pictures/setting.png", cv2.IMREAD_UNCHANGED)
BACK_ICON        = cv2.imread("assets/data/pictures/back.png",    cv2.IMREAD_UNCHANGED)
EGO_LANE_ICON    = cv2.imread("assets/data/pictures/lane.png",    cv2.IMREAD_UNCHANGED)

class DummySteeringMonitor:
    def get_feedback(self):
        return {"position": 0, "error": False}

steering_monitor = DummySteeringMonitor()
#steering_monitor = SteeringMonitor(plc)
#brake_monitor.start(callback=brake_error_callback)
#brake_monitor = BrakeErrorMonitor(plc, check_interval=0.1)

DISPLAY_ENABLED = False   # True  = user ingin lihat video

_camera_has_frames = False
_camera_status_lock = threading.Lock()

_stop_flag     = False 
_detect_thread = None 
_thread_lock   = threading.Lock()
_frame_queue: queue.Queue = queue.Queue(maxsize=2)
_on_open_settings_cb = None
_status_callback = None 

pipeline    = TrackingPipeline()
ufld        = UltrafastLaneDetector(
                  model_path="lane_detection/models/tusimple_18.pth",
                  use_gpu=True
              )
smoother    = TemporalLaneSmoother(alpha=0.7)
fcw_system  = FCW(iou_threshold=0.5, alpha=0.5)
safety_fcw  = SafetyFCWBinary(
                  conf_min=0.7,
                  ttc_hard=0.8,
                  stable_frames=5,
                  latch_time=0.5
              )
plc         = FINSInterface(plc_ip="192.168.250.1", heartbeat_interval=1.0)
ui          = ADASUI(
                  display_w=DISPLAY_W,
                  display_h=DISPLAY_H,
                  warning_logo=WARNING_LOGO,
                  steer_left_icon=STEER_LEFT_ICON,
                  steer_right_icon=STEER_RIGHT_ICON,
                  setting_icon=SETTING_ICON,
                  back_icon=BACK_ICON,
                  ego_lane_icon=EGO_LANE_ICON,
                  lane_colors=lane_colors
              )
safety_lka  = SafetyLKA(steering_monitor)

def set_open_settings_callback(cb):
    global _on_open_settings_cb
    _on_open_settings_cb = cb

def set_status_callback(cb):
    global _status_callback
    _status_callback = cb

def _set_status(msg: str):
    if _status_callback:
        _status_callback(msg)

def get_camera_status():
    with _camera_status_lock:
        return _camera_has_frames

def set_camera_status(status: bool):
    global _camera_has_frames
    with _camera_status_lock:
        _camera_has_frames = status

def _check_ignition():
    if IGNITION_CHECK_INTERVAL == 0:
        return
    try:
        val = plc.read_ignition_status()
        print(f"[IGNITION] CIO17 = {val} | Kunci = {'OFF' if val == 1 else 'ON'}")
        if val == 1:  # hanya shutdown ketika tepat 1
            print("[IGNITION] Kunci OFF — memulai shutdown Jetson...")
            stop_detection()
            import subprocess
            subprocess.run(["sudo", "/usr/sbin/shutdown", "-h", "now"], check=False)
    except Exception as e:
        print(f"[IGNITION] Gagal baca CIO17: {e}")
        # print("[IGNITION] PLC tidak merespons — memulai shutdown Jetson...")
        # stop_detection()
        # import subprocess
        # subprocess.run(["sudo", "/usr/sbin/shutdown", "-h", "now"], check=False)

def enable_display():
    global DISPLAY_ENABLED
    DISPLAY_ENABLED = True


def disable_display():
    global DISPLAY_ENABLED
    DISPLAY_ENABLED = False
    # Kosongkan queue agar frame lama tidak muncul saat display dinyalakan ulang
    _clear_frame_queue()


def get_display_frame():
    try:
        return _frame_queue.get_nowait()
    except queue.Empty:
        return None

def toggle_ego_lane_roi():
    global show_ego_lane_roi
    show_ego_lane_roi = not show_ego_lane_roi


def start_detection():
    global _stop_flag, _detect_thread

    with _thread_lock:
        if _detect_thread is not None and _detect_thread.is_alive():
            return

        _stop_flag     = False

        opt = parse_opt()
        _detect_thread = threading.Thread(
            target=_run_safe,
            args=(opt,),
            daemon=True,
            name="adas-detect"
        )
        _detect_thread.start()
        print("[DETECT] Thread started.")

def stop_detection():
    global DISPLAY_ENABLED, _stop_flag

    DISPLAY_ENABLED  = False
    _stop_flag       = True
    _clear_frame_queue()
    print("[DETECT] Stop requested.")

def _clear_frame_queue():
    while not _frame_queue.empty():
        try:
            _frame_queue.get_nowait()
        except queue.Empty:
            break


def _run_safe(opt):
    try:
        run(**vars(opt))
    except Exception as e:
        print(f"[DETECT] Error in detection thread: {e}")
    finally:
        print("[DETECT] Thread finished.")


def brake_error_callback(error: bool):
    plc.trigger_buzzer(error)


def scale_lanes(lanes_points, src_size, dst_size):
    src_w, src_h = src_size
    dst_w, dst_h = dst_size
    sx, sy = dst_w / src_w, dst_h / src_h
    return [
        [[int(x * sx), int(y * sy)] for x, y in lane]
        for lane in lanes_points
    ]

@smart_inference_mode()
def run(
    weights=ROOT / "yolov5s.pt",
    source=ROOT / "data/images",
    data=ROOT / "data/coco128.yaml",
    imgsz=(640, 640),
    conf_thres=0.25,
    iou_thres=0.45,
    max_det=1000,
    device="",
    view_img=False,
    nosave=False,
    agnostic_nms=False,
    augment=False,
    visualize=False,
    update=False,
    line_thickness=3,
    half=False,
    dnn=False,
    vid_stride=1,
):
    global DISPLAY_ENABLED, _stop_flag
    global lane_frame_id, lane_cache
    global _camera_has_frames

    source = str(source)
    
    # Inisialisasi status kamera
    set_camera_status(False)
    consecutive_failures = 0
    
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
    is_url  = source.lower().startswith(("rtsp://", "rtmp://", "http://", "https://"))
    webcam  = source.isnumeric() or source.endswith(".streams") or (is_url and not is_file)

    if is_url and is_file:
        source = check_file(source)

    # --- Load model ---
    device_obj = select_device(device)
    model      = DetectMultiBackend(weights, device=device_obj, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)
    model.warmup(imgsz=(1, 3, *imgsz))

    seen = 0

    # --- Buka kamera ---
    if webcam:
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,           30)

        if not cap.isOpened():
            print("[DETECT] ERROR: Cannot open camera")
            _set_status("Camera tidak terdeteksi — periksa koneksi kamera.")
            set_camera_status(False)
            try:
                plc.update_camera_status(False)
            except Exception as e:
                print(f"[DETECT] Failed to send camera OFF status: {e}")
            return
    else:
        print("[DETECT] ERROR: Hanya mode webcam yang didukung")
        return

    try:
        plc.update_camera_status(True)
    except Exception as e:
        print(f"[DETECT] Failed to send camera ON status: {e}")

    print("[DETECT] Detection loop started.")
    _set_status("Kamera terdeteksi — sistem ready")

    while True:
        
        frame_start = time.time()
        
        # ── Cek stop flag ──
        if _stop_flag:
            print("[DETECT] Stop flag detected, exiting loop.")
            break

        # ── Baca frame ──
        ret, im0_raw = cap.read()
        
        # Update camera status
        if ret and im0_raw is not None and im0_raw.size > 0:
            consecutive_failures = 0
            if not get_camera_status():
                set_camera_status(True)
                print("[CAMERA] Camera streaming active")
                _set_status("Kamera terdeteksi — streaming aktif")
        else:
            consecutive_failures += 1
            if consecutive_failures > 5 and get_camera_status():
                set_camera_status(False)
                print("[CAMERA] Camera stream lost")
                _set_status("⚠ Kamera tidak terdeteksi — periksa koneksi kamera")
        
        if not ret:
            print("[DETECT] Frame read error")
            break

        frame = seen
        seen += 1

        # ── Read config ──
        live_cfg = shared_config.get()

        # ── Preprocessing untuk YOLO ──
        im = cv2.resize(im0_raw, imgsz)
        im = torch.from_numpy(im).to(model.device)
        im = im.half() if model.fp16 else im.float()
        im /= 255.0
        if len(im.shape) == 3:
            im = im.permute(2, 0, 1).unsqueeze(0)

        # ── Inferensi YOLO ──
        pred = model(im, augment=augment, visualize=False)
        pred = non_max_suppression(pred, conf_thres, iou_thres, [0, 63, 2], agnostic_nms, max_det=max_det)

        det         = pred[0]
        im0_vis     = im0_raw.copy()
        detections  = []

        if det is not None and len(det):
            det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0_raw.shape).round()
            ALLOWED_CLASSES = ["person", "laptop", "car"]

            for *xyxy, conf, cls in det:
                c = int(cls)
                if names[c] not in ALLOWED_CLASSES:
                    continue
                x1, y1, x2, y2 = map(float, xyxy)
                detections.append({
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": float(conf),
                    "class":      names[c]
                })

        # ── UFLD Lane Detection (setiap N frame) ──
        lane_frame_id += 1
        if lane_frame_id % INFER_EVERY_N_FRAMES == 0 or lane_cache is None:
            lanes_points_raw, lanes_detected = ufld.detect_lanes(im0_raw)
            lane_cache = (lanes_points_raw, lanes_detected)

        lanes_points_raw, lanes_detected = lane_cache
        lanes_points = smoother.smooth(lanes_points_raw, lanes_detected)
        lanes_points = [lane if lane is not None else [] for lane in lanes_points]

        # ── Tracking ──
        tracking_results = pipeline.update(
            detections,
            w=im0_raw.shape[1],
            h=im0_raw.shape[0],
            lanes_points=lanes_points,
            lanes_detected=lanes_detected
        )
        stable_objects  = tracking_results["stable_objects"]
        ego_lane_target = tracking_results["ego_lane_target"]
        danger_vehicle  = tracking_results["danger_vehicle"]
        warning_vehicle = tracking_results["warning_vehicle"]

        # ── FCW ──
        target_obj = (
            danger_vehicle or warning_vehicle or ego_lane_target
            or (stable_objects[0] if stable_objects else None)
        )
        brake_decision = fcw_system.run(
            danger_vehicle, warning_vehicle, ego_lane_target, stable_objects,
            target_obj=target_obj,
            image_width=im0_raw.shape[1],
            image_height=im0_raw.shape[0]
        )
        safety_result  = safety_fcw.update(brake_decision)
        brake_cmd      = safety_result["brake"]

        # ── SENT FCW TO PLC ──
        plc_output = {
                "brake": brake_cmd,
                "reason": safety_result["reason"]
            }

        try:
            plc.update(plc_output)
        except Exception as e:
            print(f"[PLC] Update failed (non-fatal): {e}")
        #print("Brake 1/0", brake_cmd)

        h, w = im0_vis.shape[:2]

        scale_x = DISPLAY_W / w
        scale_y = DISPLAY_H / h
        
        # ── Annotasi bounding box ──
        annotator = Annotator(im0_vis, line_width=line_thickness)

        if ego_lane_target:
            x1, y1, x2, y2 = ego_lane_target["bbox"]
            annotator.box_label(
                [x1, y1, x2, y2],
                f"{ego_lane_target['class'].upper()} | {ego_lane_target['distance_m']} M",
                color=(0, 0, 255)
            )

        for obj in stable_objects:
            if ego_lane_target and obj["track_id"] == ego_lane_target["track_id"]:
                continue
            x1, y1, x2, y2 = obj["bbox"]
            annotator.box_label(
                [x1, y1, x2, y2],
                f"{obj['class'].upper()} | {obj['distance_m']} M",
                color=colors(obj["track_id"], True)
            )

        im0_vis = annotator.result()       
        
        # dangery/warning popup
        if danger_vehicle:
            im0_vis = ui.draw_danger_popup(im0_vis)
        elif warning_vehicle:
            im0_vis = ui.draw_warning_popup(im0_vis)

        ego_lane_data = estimate_ego_lane_data(
            lanes_points, lanes_detected,
            frame_width=im0_raw.shape[1],
            frame_height=im0_raw.shape[0],
            cfg=live_cfg
        )
        # print(ego_lane_data)

        cx = ego_lane_data.get("center_x", None)
        ego_cx = ego_lane_data.get("ego_center_x", None)

        if cx is not None:
            cx = int(cx * scale_x)

        if ego_cx is not None:
            ego_cx = int(ego_cx * scale_x)
        
        ego_lane_normalized = normalize_ego_lane(
            lanes_points=lanes_points,
            lanes_detected=lanes_detected,
            frame_width=im0_raw.shape[1],
            frame_height=im0_raw.shape[0],
            confidence=ego_lane_data["confidence"],
            center_offset=ego_lane_data["center_offset"],
            lane_width_px=ego_lane_data["lane_width_px"],
            cfg=live_cfg
        )

        steering_deg = 0.0

        if ego_lane_normalized is not None and len(ego_lane_normalized) > 0:
            # print(ego_lane_normalized)
            steering_fb         = steering_monitor.get_feedback()
            steering_actual_deg = steering_fb["position"]
            steering_error_flag = steering_fb["error"]

            steering_decision = lane_keeping_assist(
                ego_lane_normalized,
                frame_id=frame,
                prev_state=lka_state,
                steering_actual_deg=steering_actual_deg,
                cfg=live_cfg
            )

            lka_state["enable"] = steering_decision["enable"]
            lka_state["heading_error"] = (
                steering_decision["heading_error"] if steering_decision["enable"] else 0.0
            )

        else:
            steering_decision = None

        safe_steer   = safety_lka.update(steering_decision, cfg=live_cfg)
        steering_deg = safe_steer["steering_cmd_deg"] if safe_steer["valid"] else -999
        
        # ── Sent LKA to PLC ──
        plc.update_steering(
            lka_output={
                "enable": lka_state["enable"],
                "heading_error": steering_deg
            },
            max_rate_deg_per_sec=safety_lka.MAX_STEER_RATE
        )

            #print("STEERING DATA:", steering_decision)
            #print("SAFE LKA:", safe_steer)

        fps = 1.0 / (time.time() - frame_start)

        # ── Render UI overlay ──
        im0_vis = ui.draw_steering_popup(im0_vis, steering_deg)

        lanes_points_scaled = scale_lanes(
            lanes_points,
            src_size=(1280, 720),
            dst_size=(DISPLAY_W, DISPLAY_H)
        )

        im0_vis = ui.draw_info_popup(
            im0_vis,
            steering_deg=steering_deg,
            brake_cmd=brake_cmd,
            tracked_object=tracking_results,
            fps=fps
        )

        im_display = cv2.resize(im0_vis, (DISPLAY_W, DISPLAY_H))

        danger_roi     = get_danger_area_roi(DISPLAY_W, DISPLAY_H, cfg=live_cfg)
        warning_lane_roi = get_warning_area_roi(DISPLAY_W, DISPLAY_H, cfg=live_cfg)
        im_display  = ui.draw_roi_overlay(im_display, danger_roi)
        im_display  = ui.draw_roi_warning(im_display, warning_lane_roi)

        if show_ego_lane_roi:
            ego_roi    = get_ego_lane_roi(DISPLAY_W, DISPLAY_H, cfg=live_cfg)
            im_display = ui.draw_ego_lane_roi(im_display, ego_roi, lane_center_x=cx, ego_center_x=ego_cx)

        im_display = ui.draw_lanes(im_display, lanes_points_scaled, lanes_detected)
        im_display = ui.draw_overlay_buttons(im_display)

        if DISPLAY_ENABLED:
            try:
                _frame_queue.put_nowait(im_display)
            except queue.Full:
                pass 

    # Cleanup setelah loop selesai
    cap.release()
    
    # Set camera status false when detection stops
    set_camera_status(False)
    print("[CAMERA] Detection stopped, camera marked as offline")
    _set_status("Sistem berhenti — kamera offline")
    
    try:
        plc.update_camera_status(False)
    except Exception as e:
        print(f"[DETECT] Failed to send camera OFF status: {e}")

    if update:
        strip_optimizer(weights[0])


def parse_opt():
    opt = Namespace(
        weights=[ROOT / "yolov5n.pt"],
        source="0",
        device="0",
        view_img=True,
        nosave=True,
        half=True
    )
    return opt


def main(opt):
    run(**vars(opt))

if __name__ == "__main__":
    opt = parse_opt()
    start_detection()