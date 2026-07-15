import argparse
import os
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
    non_max_suppression,
    scale_boxes,
    strip_optimizer,
)
from utils.torch_utils import select_device, smart_inference_mode
from yolo.tracking_pipeline import TrackingPipeline
import cv2
import time
from argparse import Namespace
from ui.output_ui import ADASUI
from config import shared_config
from OCR.bib_manager import BibManager

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

show_ego_lane_roi = True

DISPLAY_W = 1024
DISPLAY_H = 600

WARNING_LOGO     = cv2.imread("assets/data/pictures/warning.png", cv2.IMREAD_UNCHANGED)
STEER_LEFT_ICON  = cv2.imread("assets/data/pictures/left.png",    cv2.IMREAD_UNCHANGED)
STEER_RIGHT_ICON = cv2.imread("assets/data/pictures/right.png",   cv2.IMREAD_UNCHANGED)
SETTING_ICON     = cv2.imread("assets/data/pictures/setting.png", cv2.IMREAD_UNCHANGED)
BACK_ICON        = cv2.imread("assets/data/pictures/back.png",    cv2.IMREAD_UNCHANGED)
EGO_LANE_ICON    = cv2.imread("assets/data/pictures/lane.png", cv2.IMREAD_UNCHANGED)

DISPLAY_ENABLED = False
DISPLAY_RUNNING = False
_camera_has_frames = False
_camera_status_lock = threading.Lock()

_stop_flag = False           # sinyal untuk hentikan loop run()
_detect_thread = None        # referensi thread deteksi
_thread_lock = threading.Lock()

_on_open_settings_cb = None

_mouse_x = 0
_mouse_y = 0
_mouse_clicked = False

pipeline = TrackingPipeline()
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

bib_manager = BibManager()

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
    nosave=False,  # do not save images/videos
    agnostic_nms=False,  # class-agnostic NMS
    augment=False,  # augmented inference
    visualize=False,  # visualize features
    update=False,  # update all models
    line_thickness=3,  # bounding box thickness (pixels)
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

    elif screenshot:
        dataset = LoadScreenshots(source, img_size=imgsz, stride=stride, auto=pt)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))
    seen = 0

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
            s += "{:g}x{:g} ".format(*im.shape[2:])  # print string

            # Sort
            detections = []
            
            if det is not None and len(det):
                det[:, :4] = scale_boxes(
                    im.shape[2:], # ukuran input YOLO (resize)
                    det[:, :4],
                    im0_raw.shape
                ).round()
                
                ALLOWED_CLASSES = ["person", "laptop", "car", "bib-number"]
                
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
            
            # --- INTEGRASI TRACKING PIPELINE ---
            tracking_results = pipeline.update(
                detections, 
                w=im0_raw.shape[1], 
                h=im0_raw.shape[0]
            )
                        
            h, w = im0_vis.shape[:2]

            scale_x = DISPLAY_W / w
            scale_y = DISPLAY_H / h

            annotator = Annotator(im0_vis, line_width=line_thickness)

            for obj in tracking_results["tracked_objects"]:
                x1, y1, x2, y2 = obj["bbox"]
                cls = obj["class"]
                track_id = obj["track_id"]
                dist = obj["distance_m"]
                conf = obj["confidence"]

                if cls == "bib-number":
                    pad = 0
                    x1_crop = max(int(x1 - pad),0)
                    y1_crop = max(int(y1 - pad),0)
                    x2_crop = min(int(x2 + pad), im0_raw.shape[1])
                    y2_crop = min(int(y2 + pad), im0_raw.shape[0])

                    bib_crop = im0_raw[
                        y1_crop:y2_crop,
                        x1_crop:x2_crop
                    ].copy()

                    # cv2.imwrite(
                    #     f"debug_bib_{track_id}.jpg",
                    #     bib_crop
                    # )

                    bib_result = bib_manager.update(
                        track_id,
                        bib_crop,
                        frame
                    )

                    print(
                        f"[BIB RESULT] "
                        f"ID:{track_id} "
                        f"OCR:{bib_result['ocr_number']} "
                        f"CONF:{bib_result['confidence']:.2f} "
                        f"FINAL:{bib_result['final_number']}"
                        f"LOCK:{bib_manager.memory.is_locked(track_id)} "
                        f"PROCESS:{bib_manager.memory.is_processing(track_id)} "
                        f"RETRY:{bib_manager.memory.get_retry(track_id)}"
                    )

                    if bib_result["ocr_number"] is None:
                        continue

                    annotator.box_label(
                        [x1, y1, x2, y2],
                        f"{bib_result['ocr_number']} {bib_result['confidence']:.2f}",
                        color=colors(track_id, True)
                    )

                    continue
                
                annotator.box_label(
                    [x1, y1, x2, y2],
                    f"{cls.upper()} ID:{track_id} | {conf:.2f}",
                    color=colors(track_id, True)
                )

            
            im0_vis = annotator.result()

            fps = 1.0 / (time.time() - frame_start)

            im_display = cv2.resize(im0_vis, (DISPLAY_W, DISPLAY_H))

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


    bib_manager.cleanup()
    set_camera_status(False)
    
    if DISPLAY_RUNNING:
        try:
            cv2.destroyWindow("ADAS")
        except Exception:
            pass
        DISPLAY_RUNNING = False

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
        weights=[ROOT / "best.pt"],
        source="assets/data/videos/bib_test.mp4",
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