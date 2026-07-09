import argparse
import os
#import platform
import sys
import threading
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
    #cv2,
    non_max_suppression,
    #print_args,
    scale_boxes,
    strip_optimizer,
)
from utils.torch_utils import select_device, smart_inference_mode
from yolo.tracking_pipeline import TrackingPipeline
from yolo.target_vehicle_selector import get_ego_lane_roi, get_danger_area_roi, get_warning_area_roi
#import numpy as np
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
    (0, 0, 255),    # lane 0
    (0, 255, 0),    # lane 1
    (255, 0, 0),    # lane 2
    (0, 255, 255)   # lane 3
]

INFER_EVERY_N_FRAMES = 3 # ganti ke 2 saat pakai jetson dan webcam asli
lane_frame_id = 0
lane_cache = None
lka_state = {
    "enable": False,
    "heading_error": 0.0
}

show_ego_lane_roi = True

DISPLAY_W = 1024
DISPLAY_H = 600

WARNING_LOGO     = cv2.imread("assets/data/pictures/warning.png", cv2.IMREAD_UNCHANGED)
STEER_LEFT_ICON  = cv2.imread("assets/data/pictures/left.png",    cv2.IMREAD_UNCHANGED)
STEER_RIGHT_ICON = cv2.imread("assets/data/pictures/right.png",   cv2.IMREAD_UNCHANGED)
SETTING_ICON     = cv2.imread("assets/data/pictures/setting.png", cv2.IMREAD_UNCHANGED)
BACK_ICON        = cv2.imread("assets/data/pictures/back.png",    cv2.IMREAD_UNCHANGED)
EGO_LANE_ICON    = cv2.imread("assets/data/pictures/lane.png", cv2.IMREAD_UNCHANGED)

# ---Dummy belom ada plc----
class DummySteeringMonitor:
    def get_feedback(self):
        return {"position": 0, "error": False}

steering_monitor = DummySteeringMonitor()
# --------------------------

#steering_monitor = SteeringMonitor(plc)

DISPLAY_ENABLED = False
DISPLAY_RUNNING = False
_camera_has_frames = False
_camera_status_lock = threading.Lock()

_stop_flag = False           # sinyal untuk hentikan loop run()
_detect_thread = None        # referensi thread deteksi
_thread_lock = threading.Lock()

#brake_monitor.start(callback=brake_error_callback)

_on_open_settings_cb = None

_mouse_x = 0
_mouse_y = 0
_mouse_clicked = False

pipeline = TrackingPipeline()
ufld = UltrafastLaneDetector(model_path="lane_detection/models/tusimple_18.pth", use_gpu=False)
# ufld = UltrafastLaneDetector(model_path="lane_detection/models/culane_18.pth", use_gpu=False, dataset="culane")
smoother = TemporalLaneSmoother(alpha=0.7)
fcw_system = FCW(iou_threshold=0.5, alpha=0.5)
safety_fcw = SafetyFCWBinary(
    conf_min=0.7,
    ttc_hard=0.8,
    stable_frames=5,
    latch_time=0.5
)
plc = FINSInterface(plc_ip="192.168.250.1", heartbeat_interval=1.0)
ui = ADASUI(
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
safety_lka = SafetyLKA(steering_monitor)
#brake_monitor = BrakeErrorMonitor(plc, check_interval=0.1)

def set_open_settings_callback(cb):
    global _on_open_settings_cb
    _on_open_settings_cb = cb

def get_camera_status():
    with _camera_status_lock:
        return _camera_has_frames

def set_camera_status(status: bool):
    global _camera_has_frames
    with _camera_status_lock:
        _camera_has_frames = status

def _mouse_callback(event, x, y, flags, param):
    global _mouse_x, _mouse_y, _mouse_clicked
    _mouse_x = x
    _mouse_y = y
    if event == cv2.EVENT_LBUTTONUP:
        _mouse_clicked = True

def enable_display():
    global DISPLAY_ENABLED
    DISPLAY_ENABLED = True
    
def disable_display():
    global DISPLAY_ENABLED, DISPLAY_RUNNING
    DISPLAY_ENABLED = False
    try:
        cv2.destroyWindow("ADAS")
    except Exception:
        pass
    DISPLAY_RUNNING = False

def start_detection():
    global _stop_flag, _detect_thread, DISPLAY_RUNNING

    with _thread_lock:
        if _detect_thread is not None and _detect_thread.is_alive():
            return

        _stop_flag = False

        DISPLAY_RUNNING = False

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
    global DISPLAY_ENABLED, _stop_flag, DISPLAY_RUNNING

    DISPLAY_ENABLED = False
    DISPLAY_RUNNING = False
    _stop_flag = True
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
        print("[DETECT] Stop requested.")

def _run_safe(opt):
    try:
        run(**vars(opt))
    except Exception as e:
        print(f"[DETECT] Error in detection thread: {e}")
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[DETECT] Thread finished.")

def brake_error_callback(error: bool):
    if error:
        plc.trigger_buzzer(True)
    else:
        plc.trigger_buzzer(False)

def scale_lanes(lanes_points, src_size, dst_size):
    src_w, src_h = src_size
    dst_w, dst_h = dst_size
    sx, sy = dst_w / src_w, dst_h / src_h

    scaled = []
    for lane in lanes_points:
        scaled_lane = []
        for x, y in lane:
            scaled_lane.append([int(x * sx), int(y * sy)])
        scaled.append(scaled_lane)
    return scaled

def toggle_ego_lane_roi():
    global show_ego_lane_roi
    show_ego_lane_roi = not show_ego_lane_roi

@smart_inference_mode()
def run(
    weights=ROOT / "yolov5s.pt",  # model path or triton URL
    source=ROOT / "data/images",  # file/dir/URL/glob/screen/0(webcam)
    data=ROOT / "data/coco128.yaml",  # dataset.yaml path
    imgsz=(640, 640),  # inference size (height, width)
    conf_thres=0.25,  # confidence threshold
    iou_thres=0.45,  # NMS IOU threshold
    max_det=1000,  # maximum detections per image
    device="",  # cuda device, i.e. 0 or 0,1,2,3 or cpu
    view_img=False,  # show results
    #save_txt=False,  # save results to *.txt
    #save_format=0,  # save boxes coordinates in YOLO format or Pascal-VOC format (0 for YOLO and 1 for Pascal-VOC)
    #save_csv=False,  # save results in CSV format
    #save_conf=False,  # save confidences in --save-txt labels
    #save_crop=False,  # save cropped prediction boxes
    nosave=False,  # do not save images/videos
    #classes=None,  # filter by class: --class 0, or --class 0 2 3
    agnostic_nms=False,  # class-agnostic NMS
    augment=False,  # augmented inference
    visualize=False,  # visualize features
    update=False,  # update all models
    #project=ROOT / "runs/detect",  # save results to project/name
    #name="exp",  # save results to project/name
    #exist_ok=False,  # existing project/name ok, do not increment
    line_thickness=3,  # bounding box thickness (pixels)
    #hide_labels=False,  # hide labels
    #hide_conf=False,  # hide confidences
    half=False,  # use FP16 half-precision inference
    dnn=False,  # use OpenCV DNN for ONNX inference
    vid_stride=1,  # video frame-rate stride
):
    global DISPLAY_ENABLED, DISPLAY_RUNNING, _stop_flag
    global lane_frame_id, lane_cache
    global _mouse_x, _mouse_y, _mouse_clicked
    global _camera_has_frames

    source = str(source)
    
    set_camera_status(False)
    consecutive_failures = 0
    
    #save_img = False  # save inference images
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
    is_url = source.lower().startswith(("rtsp://", "rtmp://", "http://", "https://"))
    webcam = source.isnumeric() or source.endswith(".streams") or (is_url and not is_file)
    screenshot = source.lower().startswith("screen")
    if is_url and is_file:
        source = check_file(source)  # download

    # Cek source video file 
    if not webcam and not screenshot and is_file:
        if not Path(source).exists():
            print(f"[DETECT] ERROR: Source video tidak ditemukan: {source}")
            try:
                plc.update_camera_status(False)
            except Exception as e:
                print(f"[DETECT] Failed to send camera OFF status: {e}")
            return

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader
    bs = 1  # batch_size
    if webcam:
        view_img = check_imshow(warn=True)

        #---webcam laptop
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        bs = len(dataset)

        #---webcam asli
        # cap = cv2.VideoCapture(int(source))  # index webcam USB
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)   # lock width
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)   # lock height
        # cap.set(cv2.CAP_PROP_FPS, 30)             # lock FPS
        # 
        # # loop pengambilan frame
        # while True:
        #     ret, im0 = cap.read()
        #     if not ret:
        #         break
        #     # lanjutkan pipeline seperti biasa

    elif screenshot:
        dataset = LoadScreenshots(source, img_size=imgsz, stride=stride, auto=pt)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)

    # kirim status kamera ketika ON ke plc
    try:
        plc.update_camera_status(True)
    except Exception as e:
        print(f"[DETECT] Failed to send camera ON status: {e}")

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))
    seen = 0
    #windows = []

    for path, im, im0s, vid_cap, s in dataset:

        frame_start = time.time()

        if _stop_flag:
            print("[DETECT] Stop flag detected, exiting loop.")
            break

        if im0s is not None and len(im0s) > 0:
            consecutive_failures = 0
            if not get_camera_status():
                set_camera_status(True)
                print("[CAMERA] Camera streaming active")
        else:
            consecutive_failures += 1
            if consecutive_failures > 5 and get_camera_status():
                set_camera_status(False)
                print("[CAMERA] Camera stream lost")

        # Baca config
        live_cfg = shared_config.get()

        im = torch.from_numpy(im).to(model.device)
        im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
        im /= 255  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim

        # Inference
        visualize = False
        pred = model(im, augment=augment, visualize=visualize)
        pred = non_max_suppression(pred, conf_thres, iou_thres, [0, 63, 2], agnostic_nms, max_det=max_det)

        # Process predictions
        for i, det in enumerate(pred):  # per image
            seen += 1
            if webcam:  # batch_size >= 1
                p, im0_raw, frame = path[i], im0s[i].copy(), dataset.count
                s += f"{i}: "
            else:
                p, im0_raw, frame = path, im0s.copy(), getattr(dataset, "frame", 0)

            im0_vis = im0_raw.copy()

            p = Path(p)  # to Path
            #save_path = None
            #txt_path = None
            s += "{:g}x{:g} ".format(*im.shape[2:])  # print string
            #gn = torch.tensor(im0_raw.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            #imc = im0_raw.copy() if save_crop else im0_raw  # for save_crop
            #track_classes = {}

            # Sort
            detections = []
            
            if det is not None and len(det):
                det[:, :4] = scale_boxes(
                    im.shape[2:], # ukuran input YOLO (resize)
                    det[:, :4],
                    im0_raw.shape
                ).round()
                
                ALLOWED_CLASSES = ["person", "laptop", "car"]
                
                for *xyxy, conf, cls in det:
                    c = int(cls)
                    if names[c] not in ALLOWED_CLASSES:
                        continue
                    x1, y1, x2, y2 = map(float, xyxy)
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(conf),
                        "class": names[c]
                    })
            
            # ===============================
            # UFLD LANE DETECTION
            # ===============================
            lane_frame_id += 1

            if lane_frame_id % INFER_EVERY_N_FRAMES == 0 or lane_cache is None:
                lanes_points_raw, lanes_detected = ufld.detect_lanes(im0_raw)
                lane_cache = (lanes_points_raw, lanes_detected)

            lanes_points_raw, lanes_detected = lane_cache
            
            #print("raw:", lanes_points_raw)

            lanes_points = smoother.smooth(lanes_points_raw, lanes_detected)
            lanes_points = [lane if lane is not None else [] for lane in lanes_points]

            # --- INTEGRASI TRACKING PIPELINE ---
            tracking_results = pipeline.update(
                detections, 
                w=im0_raw.shape[1], 
                h=im0_raw.shape[0],
                lanes_points=lanes_points,
                lanes_detected=lanes_detected
            )

            stable_objects   = tracking_results["stable_objects"]
            ego_lane_target  = tracking_results["ego_lane_target"]
            danger_vehicle   = tracking_results["danger_vehicle"]
            warning_vehicle  = tracking_results["warning_vehicle"]
            # --------------------------------------------------

            # --- RUN FCW ---
            # Pilih kendaraan target untuk ego lane (prioritas ego_lane_target)
            if danger_vehicle:
                target_obj = danger_vehicle
            elif warning_vehicle:
                target_obj = warning_vehicle
            elif ego_lane_target:
                target_obj = ego_lane_target
            elif stable_objects:
                target_obj = stable_objects[0]
            else:
                target_obj = None

            brake_decision = fcw_system.run(
                danger_vehicle,
                warning_vehicle,
                ego_lane_target,
                stable_objects,
                target_obj=target_obj,
                image_width=im0_raw.shape[1],
                image_height=im0_raw.shape[0]
            )

            #print("FCW:", brake_decision)

            # --- SAFETY FCW ---
            safety_result = safety_fcw.update(brake_decision)

            #print("SAFETY FCW:", safety_result)

            brake_cmd = safety_result["brake"]
            plc_output = {
                "brake": brake_cmd,
                "reason": safety_result["reason"]
            }
            
            # try:
            #     plc.update(plc_output)
            # except Exception as e:
            #     print(f"[PLC] Update failed (non-fatal): {e}")
                        
            h, w = im0_vis.shape[:2]

            scale_x = DISPLAY_W / w
            scale_y = DISPLAY_H / h

            annotator = Annotator(im0_vis, line_width=line_thickness)

            # Tampilkan ego lane target & danger_vehicle
            if ego_lane_target:
                x1, y1, x2, y2 = ego_lane_target["bbox"]
                cls = ego_lane_target["class"]
                dist = ego_lane_target["distance_m"]
                annotator.box_label([x1, y1, x2, y2], f"{cls.upper()} | {dist} M", color=(0, 0, 255))

            for obj in stable_objects:
                if ego_lane_target and obj["track_id"] == ego_lane_target["track_id"]:
                    continue
                x1, y1, x2, y2 = obj["bbox"]
                cls = obj["class"]
                track_id = obj["track_id"]
                dist = obj["distance_m"]
                annotator.box_label(
                    [x1, y1, x2, y2],
                    f"{cls.upper()} | {dist} M",
                    color=colors(track_id, True)
                )

            # print("DRAWING:", stable_objects)
            
            im0_vis = annotator.result()

            # dangery/warning popup
            if danger_vehicle:
                im0_vis = ui.draw_danger_popup(im0_vis)
            elif warning_vehicle:
                im0_vis = ui.draw_warning_popup(im0_vis)

            # --------EGO LANE ESTIMATION
            ego_lane_data = estimate_ego_lane_data(
                lanes_points, lanes_detected,
                frame_width=im0_raw.shape[1],
                frame_height=im0_raw.shape[0],
                cfg=live_cfg
            )
            
            
            cx = ego_lane_data.get("center_x", None)
            ego_cx = ego_lane_data.get("ego_center_x", None)

            if cx is not None:
                cx = int(cx * scale_x)

            if ego_cx is not None:
                ego_cx = int(ego_cx * scale_x)
            
            # print(f"[DEBUG] ego_lane_data conf: {ego_lane_data['confidence']:.3f}")

            #print("smoothing:", lanes_points)
            #print("ego lane:", ego_lane_data)

            # --------EGO LANE NORMALIZATION
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
            
            # print(f"[DEBUG] ego_lane_normalized: {ego_lane_normalized}")

            steering_deg = 0.0

            if ego_lane_normalized:           
                # --- ambil feedback posisi setir dari PLC (contoh: register D10)
                steering_fb = steering_monitor.get_feedback()
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

                if steering_decision["enable"]:
                    lka_state["heading_error"] = steering_decision["heading_error"]
                else:
                    lka_state["heading_error"] = 0.0
            else:
                steering_decision = None
            
            safe_steer = safety_lka.update(
                steering_decision,
                cfg=live_cfg
            )

            steering_deg = safe_steer["steering_cmd_deg"]
            
            # if steering_decision:
            #     print(f"[DEBUG] steering_decision: enable={steering_decision['enable']}, heading={steering_decision['heading_error']:.3f}")
            # print(f"[DEBUG] safe_steer: {safe_steer}")

            fps = 1.0 / (time.time() - frame_start)

            # plc.update_steering(
            #    lka_output={
            #        "enable": lka_state["enable"],
            #        "heading_error": steering_deg
            #    },
            #    max_rate_deg_per_sec=safety_lka.MAX_STEER_RATE
            # )

            # print("STEERING DATA:", steering_decision)
            # print("SAFE LKA:", safe_steer)

            im0_vis = ui.draw_steering_popup(
                im0_vis,
                steering_deg
            )
            
            # scale dari 1280x720 → ukuran im0
            lanes_points_scaled = scale_lanes(
                lanes_points,
                # src_size=(1280, 720),
                src_size=(im0_raw.shape[1], im0_raw.shape[0]),
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
            
            # --- GAMBAR ROI LANE ---
            danger_roi = get_danger_area_roi(DISPLAY_W, DISPLAY_H, cfg=live_cfg)
            im_display = ui.draw_roi_overlay(
                im_display,
                danger_roi
            )

            warning_lane_roi = get_warning_area_roi(DISPLAY_W, DISPLAY_H, cfg=live_cfg)
            im_display = ui.draw_roi_warning(
                im_display,
                warning_lane_roi
            )

            if show_ego_lane_roi:
                ego_roi = get_ego_lane_roi(DISPLAY_W, DISPLAY_H, cfg=live_cfg)
                im_display = ui.draw_ego_lane_roi(im_display, ego_roi, lane_center_x=cx, ego_center_x=ego_cx)

            im_display = ui.draw_lanes(im_display, lanes_points_scaled, lanes_detected)

            im_display = ui.draw_overlay_buttons(im_display)

            if DISPLAY_ENABLED:
                # Buat window pertama kali jika belum ada
                if not DISPLAY_RUNNING:
                    cv2.namedWindow("ADAS", cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
                    cv2.resizeWindow("ADAS", DISPLAY_W, DISPLAY_H)
                    cv2.setMouseCallback("ADAS", _mouse_callback)
                    DISPLAY_RUNNING = True

                cv2.imshow("ADAS", im_display)

                if _mouse_clicked:
                    _mouse_clicked = False
                    if ui.is_click_back(_mouse_x, _mouse_y):
                        disable_display()
                    elif ui.is_click_setting(_mouse_x, _mouse_y):
                        disable_display()
                        if _on_open_settings_cb is not None:
                            _on_open_settings_cb()
                    elif ui.is_click_ego_toggle(_mouse_x, _mouse_y): 
                        toggle_ego_lane_roi()

                key = cv2.waitKey(1) & 0xFF

                try:
                    visible = cv2.getWindowProperty("ADAS", cv2.WND_PROP_VISIBLE)
                except cv2.error:
                    visible = -1

                if visible < 1 or key == ord('q'):
                    DISPLAY_ENABLED = False
                    DISPLAY_RUNNING = False
                    try:
                        cv2.destroyWindow("ADAS")
                    except Exception:
                        pass
            else:
                if DISPLAY_RUNNING:
                    try:
                        cv2.destroyWindow("ADAS")
                    except Exception:
                        pass
                    DISPLAY_RUNNING = False
                cv2.waitKey(1)


    set_camera_status(False)
    # print("[CAMERA] Detection stopped, camera marked as offline")
    
    if DISPLAY_RUNNING:
        try:
            cv2.destroyWindow("ADAS")
        except Exception:
            pass
        DISPLAY_RUNNING = False

    # kirim status kamera OFF ke plc
    try:
        plc.update_camera_status(False)
    except Exception as e:
        print(f"[DETECT] Failed to send camera OFF status: {e}")

    if update:
        strip_optimizer(weights[0])


def parse_opt():
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", nargs="+", type=str, default=ROOT / "yolov5s.pt", help="model path or triton URL")
    parser.add_argument("--source", type=str, default=ROOT / "data/images", help="file/dir/URL/glob/screen/0(webcam)")
    parser.add_argument("--data", type=str, default=ROOT / "data/coco128.yaml", help="(optional) dataset.yaml path")
    parser.add_argument("--imgsz", "--img", "--img-size", nargs="+", type=int, default=[640], help="inference size h,w")
    parser.add_argument("--conf-thres", type=float, default=0.25, help="confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.45, help="NMS IoU threshold")
    parser.add_argument("--max-det", type=int, default=1000, help="maximum detections per image")
    parser.add_argument("--device", default="", help="cuda device, i.e. 0 or 0,1,2,3 or cpu")
    parser.add_argument("--view-img", action="store_true", help="show results")
    parser.add_argument("--save-txt", action="store_true", help="save results to *.txt")
    parser.add_argument(
        "--save-format",
        type=int,
        default=0,
        help="whether to save boxes coordinates in YOLO format or Pascal-VOC format when save-txt is True, 0 for YOLO and 1 for Pascal-VOC",
    )
    parser.add_argument("--save-csv", action="store_true", help="save results in CSV format")
    parser.add_argument("--save-conf", action="store_true", help="save confidences in --save-txt labels")
    parser.add_argument("--save-crop", action="store_true", help="save cropped prediction boxes")
    parser.add_argument("--nosave", action="store_true", help="do not save images/videos")
    parser.add_argument("--classes", nargs="+", type=int, help="filter by class: --classes 0, or --classes 0 2 3")
    parser.add_argument("--agnostic-nms", action="store_true", help="class-agnostic NMS")
    parser.add_argument("--augment", action="store_true", help="augmented inference")
    parser.add_argument("--visualize", action="store_true", help="visualize features")
    parser.add_argument("--update", action="store_true", help="update all models")
    parser.add_argument("--project", default=ROOT / "runs/detect", help="save results to project/name")
    parser.add_argument("--name", default="exp", help="save results to project/name")
    parser.add_argument("--exist-ok", action="store_true", help="existing project/name ok, do not increment")
    parser.add_argument("--line-thickness", default=3, type=int, help="bounding box thickness (pixels)")
    parser.add_argument("--hide-labels", default=False, action="store_true", help="hide labels")
    parser.add_argument("--hide-conf", default=False, action="store_true", help="hide confidences")
    parser.add_argument("--half", action="store_true", help="use FP16 half-precision inference")
    parser.add_argument("--dnn", action="store_true", help="use OpenCV DNN for ONNX inference")
    parser.add_argument("--vid-stride", type=int, default=1, help="video frame-rate stride")
    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
    print_args(vars(opt))
    """
    #----versi harcode JETSON
    opt = Namespace(
        weights=[ROOT / "yolov5n.pt"],
        source="assets/data/videos/ADAS_testing_video.mp4",
        # source="0",
        device="CPU",
        view_img=True,
        nosave=True,
        half=False
    )
    return opt

def main(opt):
    run(**vars(opt))

if __name__ == "__main__":
    opt = parse_opt()
    start_detection()