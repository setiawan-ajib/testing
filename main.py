import sys
import traceback
import threading
import cv2
import numpy as np

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore    import QPropertyAnimation, QEasingCurve, QRect, Qt, QTimer
from PyQt5.QtGui     import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

from config.config_wiring import (
    wire_config_panel,
    wire_lane_lka_panel,
    get_config_values,
    get_lane_lka_values,
    set_config_values,
    set_lane_lka_values,
    reset_config_values,
    reset_lane_lka_values,
)
from config import shared_config
import last_detect
from plc_omron.setting_interface import UIFINSForwarder
from config.settings_store import save_settings, load_settings
from last_detect import IGNITION_CHECK_INTERVAL
from utils.click_sound import ClickSoundFilter

def _lbl(text):
    return (
        '<span style="background-color: rgba(255,255,255,100);'
        ' border-radius: 6px; padding: 4px 12px;'
        ' color: white; font-weight: bold;">'
        f'&nbsp;{text}&nbsp;</span>'
        '<p style="margin: 8px 0 0 0;">'
    )

def _body(content):
    return content + '</p>'

INFO_TEXT = {
    "spinSteeringResp": (
        "Steering Responsiveness",
        _body(f"{_lbl('Steering Responsiveness')}Mengatur seberapa agresif setir kembali ke jalur.")
    ),
    "spinSteadyState": (
        "Steady-State Correction",
        _body(
            f"{_lbl('Steady-State Correction')}"
            "Menghilangkan error kecil yang menetap saat mobil berjalan lurus."
            "Koreksi akumulatif agar kendaraan tetap di tengah jalur."
        )
    ),
    "spinDamping": (
        "Damping / Stability",
        _body(f"{_lbl('Damping / Stability')}Meredam setir agar tidak goyang saat melakukan koreksi.")
    ),
    "spinCorrectionLimit": (
        "Correction Limit",
        _body(f"{_lbl('Correction Limit')}Batas maksimal akumulasi koreksi untuk mencegah overshoot saat manuver.")
    ),
    "spinSteeringCenterOffset": (
        "Steering Center Offset",
        _body(f"{_lbl('Steering Center Offset')}Kalibrasi titik tengah setir jika mobil agak narik ke salah satu sisi.")
    ),
    "spinObstacleBuffer": (
        "Obstacle Detection Buffer",
        _body(f"{_lbl('Obstacle Detection Buffer')}Jarak aman minimal (meter) sebelum sistem melakukan intervensi rem otomatis.")
    ),
    "spinSensitivity": (
        "Sensitivity Threshold",
        _body(f"{_lbl('Sensitivity Threshold')}Ambang batas kepercayaan deteksi objek.")
    ),
    "spinBrakingLatency": (
        "Braking Latency / Delay",
        _body(f"{_lbl('Braking Latency / Delay')}Kompensasi jeda waktu (ms) antara perintah sistem ke mekanik rem.")
    ),
    "spinTTC": (
        "Collision Warning Time (TTC)",
        _body(f"{_lbl('Collision Warning Time (TTC)')}Time-to-Collision dalam detik sebelum alarm peringatan tabrakan berbunyi.")
    ),
    "spinVehicleWidth": (
        "Vehicle Reference Width",
        _body(
            f"{_lbl('Vehicle Reference Width')}"
            "Lebar acuan kendaraan dalam meter.<br><br>"
            "Digunakan untuk estimasi jarak lateral terhadap batas jalur &amp; obstacle."
        )
    ),
    "spinScaleFactor": (
        "Scale Factor (px/m)",
        _body(
            f"{_lbl('Scale Factor (px/m)')}"
            "Rasio konversi piksel kamera ke satuan metrik (px/m).<br><br>"
            "Nilai bergantung pada resolusi kamera dan tinggi mounting."
        )
    ),
    "spinCameraHeight": (
        "Camera Mounting Height",
        _body(
            f"{_lbl('Camera Mounting Height')}"
            "Tinggi kamera dari permukaan aspal (meter).<br><br>"
            "Parameter penting untuk perhitungan perspektif dan depth estimation."
        )
    ),
    "spinLookAhead": (
        "Look-Ahead Distance",
        _body(
            f"{_lbl('Look-Ahead Distance')}"
            "Jarak pandang virtual (meter) untuk menentukan lintasan yang akan diikuti kendaraan."
        )
    ),
    "spinPointDensityRef": (
        "Point Density Reference",
        _body(
            f"{_lbl('Point Density Reference')}"
            "Referensi jumlah titik lane untuk normalisasi confidence (point density score).<br><br>"
            "Rumus: <b>min(num_points / ref, 0.4)</b><br>"
            "Semakin kecil nilai ini, semakin cepat confidence mencapai maksimum.<br>"
            "Default 120 — turunkan ke 80–90 jika lane sering dianggap low-confidence "
            "padahal deteksi terlihat baik."
        )
    ),
    "spinCurvSoft": (
        "Curvature Soft Threshold",
        _body(
            f"{_lbl('Curvature Soft Threshold')}"
            "Ambang kelengkungan di bawahnya curvature score = 1.0 (confidence penuh).<br><br>"
            "Naikkan ke 0.005 jika jalur sedikit melengkung masih di-flag low-confidence.<br>"
            "Harus selalu lebih kecil dari Curvature Hard Threshold."
        )
    ),
    "spinCurvHard": (
        "Curvature Hard Threshold",
        _body(
            f"{_lbl('Curvature Hard Threshold')}"
            "Ambang kelengkungan di atasnya curvature score = 0 (confidence drop penuh).<br><br>"
            "Naikkan ke 0.015 jika tikungan normal menyebabkan confidence terlalu rendah.<br>"
            "Harus selalu lebih besar dari Curvature Soft Threshold."
        )
    ),
    # "spinCurvNoiseGate": (
    #     "Curvature Noise Gate",
    #     _body(
    #         f"{_lbl('Curvature Noise Gate')}"
    #         "Gate kelengkungan untuk aktivasi offset jump penalty.<br><br>"
    #         "Bila abs(curvature) di bawah nilai ini, penalty lompatan offset lebih sensitif.<br>"
    #         "Naikkan ke 0.004–0.005 untuk mengurangi false penalty di jalan lurus."
    #     )
    # ),
    "spinKHead": (
        "Heading Correction Gain (K_HEAD)",
        _body(
            f"{_lbl('Heading Correction Gain (K_HEAD)')}"
            "Mengatur seberapa kuat sistem mengoreksi arah kendaraan agar sejajar dengan jalur.<br><br>"
            "Nilai lebih tinggi membuat respons lebih cepat, tetapi bisa menyebabkan "
            "gerakan zig-zag jika terlalu besar."
        )
    ),
    "spinOffsetJumpThresh": (
        "Offset Jump Threshold",
        _body(
            f"{_lbl('Offset Jump Threshold')}"
            "Threshold lompatan center_offset antar frame, dalam fraksi lebar frame.<br><br>"
            "Bila perubahan offset &gt; nilai ini × frame_width, "
            "confidence dikurangi 0.3 (noise penalty).<br>"
            "Turunkan ke 0.05–0.07 untuk deteksi lompatan lebih agresif."
        )
    ),
    # "spinDxNoiseGate": (
    #     "Heading dx Noise Gate (m)",
    #     _body(
    #         f"{_lbl('Heading dx Noise Gate')}"
    #         "Threshold minimum perubahan lateral lane center (meter) "
    #         "agar curvature_1pm dihitung.<br><br>"
    #         "Mencegah pembagian dengan nilai sangat kecil saat jalan hampir lurus.<br>"
    #         "Bisa diset ke <b>panjang_lane × 0.005</b> sebagai alternatif."
    #     )
    # ),
    "spinKLat": (
        "Lateral Correction Gain (K_LAT)",
        _body(
            f"{_lbl('Lateral Correction Gain (K_LAT)')}"
            "Mengatur seberapa kuat sistem mengembalikan kendaraan ke tengah jalur.<br><br>"
            "Nilai lebih tinggi membuat kendaraan lebih cepat kembali ke tengah, "
            "tetapi bisa terasa agresif jika terlalu besar."
        )
    ),
    "spinNormConfMin": (
        "Normalize Min Confidence",
        _body(
            f"{_lbl('Normalize Min Confidence')}"
            "Confidence minimum agar <i>normalize_ego_lane</i> mengembalikan data "
            "(tidak return None).<br><br>"
            "Kurangi ke 0.40–0.45 jika sistem terlalu sering tidak menghasilkan "
            "data normalize di kondisi normal."
        )
    ),
    "spinMaxRateDeg": (
        "Max Steer Rate (deg/s)",
        _body(
            f"{_lbl('Max Steer Rate')}"
            "Kecepatan maksimal perubahan heading command per detik.<br><br>"
            "Turunkan ke <b>10–12</b> untuk koreksi lebih halus dan nyaman.<br>"
            "Naikkan ke <b>18</b> untuk respons lebih cepat "
            "(berpotensi terasa 'snap' di tikungan)."
        )
    ),
    "spinDeadzoneHeading": (
        "Deadzone Heading (deg)",
        _body(
            f"{_lbl('Deadzone Heading')}"
            "Bila heading command &lt; nilai ini <b>dan</b> lateral error &lt; "
            "Deadzone Lateral, command di-zero.<br><br>"
            "Mencegah micro-koreksi terus-menerus saat kendaraan hampir di center jalur.<br>"
            "Turunkan ke 0.20 untuk koreksi lebih responsif saat mendekati center."
        )
    ),
    "spinDeadzoneLateral": (
        "Deadzone Lateral (m)",
        _body(
            f"{_lbl('Deadzone Lateral')}"
            "Lateral error di bawah nilai ini (bersama Deadzone Heading) akan di-zero.<br><br>"
            "Turunkan ke 0.08 untuk koreksi lebih sensitif saat offset kecil."
        )
    ),
    "spinSteerMargin": (
        "Steer Saturation Margin (deg)",
        _body(
            f"{_lbl('Steer Saturation Margin')}"
            "Jarak dari MAX_STEER_ABS di mana gain mulai diturunkan (fade-out zone).<br><br>"
            "Gain akan linear fade ke 0 saat steering mendekati batas absolut.<br>"
            "Kurangi ke 0.3 agar fade dimulai lebih dekat ke batas."
        )
    ),
    "spinMaxSteerAbs": (
        "Max Steering Command (deg)",
        _body(
            f"{_lbl('Max Steering Command')}"
            "Batas absolut heading command yang dikirim ke aktuator dari LKA.<br><br>"
            "Nilai <b>5–7 deg</b> aman untuk LKA highway.<br>"
            "Jangan naikkan mendekati 45 deg — itu batas mekanik, bukan batas LKA."
        )
    ),
    "spinSafetyMinConf": (
        "Safety Min Confidence",
        _body(
            f"{_lbl('Safety Min Confidence')}"
            "Confidence minimum di SafetyLKA agar steering command diizinkan keluar "
            "ke aktuator.<br><br>"
            "Ini adalah filter terakhir sebelum aktuasi fisik.<br>"
            "Sebaiknya sama atau lebih tinggi dari CONF_ON di LKA Control."
        )
    ),
    "spinSafetyMaxSteer": (
        "Safety Max Steer Clamp (deg)",
        _body(
            f"{_lbl('Safety Max Steer Clamp')}"
            "Batas keras SafetyLKA untuk clamp steering command akhir sebelum dikirim ke PLC.<br><br>"
            "Nilai ini mengoverride semua output dari lka.py.<br>"
            "<b>Pastikan selalu ≤ Max Steering Command</b> di bagian LKA Control Parameters."
        )
    ),
}

INFO_BTN_MAP = {
    "btnInfoSteeringResp":         "spinSteeringResp",
    "btnInfoSteadyState":          "spinSteadyState",
    "btnInfoDamping":              "spinDamping",
    "btnInfoCorrectionLimit":      "spinCorrectionLimit",
    "btnInfoSteeringCenterOffset": "spinSteeringCenterOffset",
    "btnInfoObstacleBuffer":       "spinObstacleBuffer",
    "btnInfoSensitivity":          "spinSensitivity",
    "btnInfoBrakingLatency":       "spinBrakingLatency",
    "btnInfoTTC":                  "spinTTC",
    "btnInfoVehicleWidth":         "spinVehicleWidth",
    "btnInfoScaleFactor":          "spinScaleFactor",
    "btnInfoCameraHeight":         "spinCameraHeight",
    "btnInfoLookAhead":            "spinLookAhead",
}

INFO_BTN_MAP_LANE_LKA = {
    "btnInfoPointDensityRef2":      "spinPointDensityRef",
    "btnInfoCurvSoft2":             "spinCurvSoft",
    "btnInfoCurvHard2":             "spinCurvHard",
    # "btnInfoCurvNoiseGate2":        "spinCurvNoiseGate",
    "btnInfoKHead2":                "spinKHead",
    "btnInfoOffsetJumpThresh2":     "spinOffsetJumpThresh",
    # "btnInfoDxNoiseGate2":          "spinDxNoiseGate",
    "btnInfoKLat2":                 "spinKLat",
    "btnInfoNormConfMin2":          "spinNormConfMin",
    "btnInfoMaxRateDeg2":           "spinMaxRateDeg",
    "btnInfoDeadzoneHeading2":      "spinDeadzoneHeading",
    "btnInfoDeadzoneLateral2":      "spinDeadzoneLateral",
    "btnInfoSteerMargin2":          "spinSteerMargin",
    "btnInfoMaxSteerAbs2":          "spinMaxSteerAbs",
    "btnInfoSafetyMinConf2":        "spinSafetyMinConf",
    "btnInfoSafetyMaxSteer2":       "spinSafetyMaxSteer",
}


class VideoWindow(QtWidgets.QWidget):

    def __init__(self, display_w, display_h, on_back=None, on_setting=None, parent=None):
        super().__init__(parent)
        self.display_w   = display_w
        self.display_h   = display_h
        self._on_back    = on_back
        self._on_setting = on_setting

        self.setWindowTitle("ADAS")
        self.setFixedSize(display_w, display_h)
        self.setStyleSheet("background-color: black;")
        self.setWindowFlags(Qt.Window)

        # QLabel sebagai canvas frame
        self._label = QLabel(self)
        self._label.setGeometry(0, 0, display_w, display_h)
        self._label.setAlignment(Qt.AlignCenter)

    def update_frame(self, frame_bgr: np.ndarray):
        frame_rgb      = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch       = frame_rgb.shape
        bytes_per_line = ch * w
        q_img  = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self._label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            if last_detect.ui.is_click_back(x, y):
                if self._on_back:
                    self._on_back()
                return
            if last_detect.ui.is_click_setting(x, y):
                if self._on_setting:
                    self._on_setting()
                return

            if last_detect.ui.is_click_ego_toggle(x, y):
                last_detect.toggle_ego_lane_roi()
                return

    def closeEvent(self, event):
        if self._on_back:
            self._on_back()
        event.accept()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        uic.loadUi("ui/menu.ui", self)

        self.statusbar.showMessage("System Ready...")
        self.panelConfiguration.hide()
        self.panelLaneLKA.hide()

        # Wire panels first before loading from PLC
        wire_config_panel(self)
        wire_lane_lka_panel(self)

        # Init forwarder then load config from PLC
        self._forwarder = UIFINSForwarder()
        
        # Tambahkan atribut untuk tracking status koneksi
        self._plc_connected = False
        self._camera_connected = False
        
        self._auto_load_last_settings()

        # Panel 1 (Configuration)
        panel = self.panelConfiguration
        self._anim_open = QPropertyAnimation(panel, b"geometry")
        self._anim_open.setDuration(300)
        self._anim_open.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_close = QPropertyAnimation(panel, b"geometry")
        self._anim_close.setDuration(250)
        self._anim_close.setEasingCurve(QEasingCurve.InCubic)
        self._anim_close.finished.connect(self._on_panel_close_finished)

        # Panel 2 (Lane LKA)
        panel2 = self.panelLaneLKA
        self._anim_open2 = QPropertyAnimation(panel2, b"geometry")
        self._anim_open2.setDuration(300)
        self._anim_open2.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_close2 = QPropertyAnimation(panel2, b"geometry")
        self._anim_close2.setDuration(250)
        self._anim_close2.setEasingCurve(QEasingCurve.InCubic)
        self._anim_close2.finished.connect(self._on_panel2_close_finished)

        self.btnStart.setCheckable(True)
        self.btnStart.clicked.connect(self.toggle_display)
        self.btnConfiguration.clicked.connect(self.toggle_config_panel)
        self.btnClosePanel.clicked.connect(self.close_config_panel)
        self.btnSaveConfig.clicked.connect(self.save_config)
        self.btnResetConfig.clicked.connect(self.reset_config)
        self.btnLoadLastConfig.clicked.connect(self.load_last_config)

        self.btnLaneLKA.clicked.connect(self.toggle_lane_lka_panel)
        self.btnClosePanelLane.clicked.connect(self.close_lane_lka_panel)
        self.btnSaveLaneLKA.clicked.connect(self.save_lane_lka)
        self.btnResetLaneLKA.clicked.connect(self.reset_lane_lka)
        self.btnLoadLastLaneLKA.clicked.connect(self.load_last_lane_lka)

        self._active_info_key = None
        self._info_buttons    = {}
        self._connect_info_buttons()
        self._setup_overlay_widgets()
        self._show_adas_description()

        self._video_window = VideoWindow(
            display_w  = last_detect.DISPLAY_W,
            display_h  = last_detect.DISPLAY_H,
            on_back    = self._on_video_back,
            on_setting = self._on_video_open_settings,
        )

        # ── Timer render frame ~30 FPS ──
        self._display_timer = QTimer(self)
        self._display_timer.setInterval(33)
        self._display_timer.timeout.connect(self._update_video_frame)
        self._display_timer.start()

        # ── Timer sinkronisasi btnStart ──
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(500)
        self._sync_timer.timeout.connect(self._sync_display_state)
        self._sync_timer.start()
        
        if IGNITION_CHECK_INTERVAL > 0:
            self._ignition_timer = QTimer(self)
            self._ignition_timer.setInterval(IGNITION_CHECK_INTERVAL * 1000)  # ms
            self._ignition_timer.timeout.connect(last_detect._check_ignition)
            self._ignition_timer.start()
            print(f"[IGNITION] Auto-shutdown aktif, cek M17 tiap {IGNITION_CHECK_INTERVAL}s.")
        else:
            self._ignition_timer = None
            print("[IGNITION] Auto-shutdown dinonaktifkan (IGNITION_CHECK_INTERVAL = 0).")
        
        # Timer untuk polling status PLC dan Camera
        self._plc_check_timer = QTimer(self)
        self._plc_check_timer.setInterval(6000)
        self._plc_check_timer.timeout.connect(self._poll_plc_connection)
        self._plc_check_timer.start()
        
        self._camera_check_timer = QTimer(self)
        self._camera_check_timer.setInterval(6000)
        self._camera_check_timer.timeout.connect(self._poll_camera_status)
        self._camera_check_timer.start()
        
        QTimer.singleShot(8000, self._initial_connection_check)

        self._start_detection_background()

        last_detect.set_open_settings_callback(self._on_video_open_settings)

    def _auto_load_last_settings(self):
        data = load_settings()
        if not data:
            print("[SETTINGS] Tidak ada file tersimpan, pakai default.")
            return

        # Lane & LKA
        if "lane_lka" in data:
            set_lane_lka_values(self, data["lane_lka"])
            shared_config.update(data["lane_lka"])
            print("[SETTINGS] Lane & LKA auto-loaded dari file.")

        status = self.statusbar.currentMessage()
        if "default" in status.lower() or "not connected" in status.lower():
            if "config" in data:
                set_config_values(self, data["config"])
                print("[SETTINGS] Config Hardware auto-loaded dari file (PLC offline).")

    def load_last_config(self):
        data = load_settings()
        if data and "config" in data:
            set_config_values(self, data["config"])
            self.statusbar.showMessage(
                "Last saved Config Hardware loaded. Klik SAVE untuk kirim ke PLC."
            )
            print("[SETTINGS] Config Hardware manually loaded dari file.")
        else:
            self.statusbar.showMessage(
                "Belum ada settings tersimpan — atur dulu lalu klik SAVE."
            )

    def load_last_lane_lka(self):
        data = load_settings()
        if data and "lane_lka" in data:
            set_lane_lka_values(self, data["lane_lka"])
            self.statusbar.showMessage(
                "Last saved Lane & LKA loaded. Klik SAVE untuk apply."
            )
            print("[SETTINGS] Lane & LKA manually loaded dari file.")
        else:
            self.statusbar.showMessage(
                "Belum ada settings tersimpan — atur dulu lalu klik SAVE."
            )
    
    def _load_config_from_plc(self):
        print("[LOAD FROM PLC] ── Starting config load from PLC ──")

        try:
            plc_cfg = self._forwarder.read_ui_params()

            if plc_cfg is None:
                print(
                    "[LOAD FROM PLC] FAILED: read_ui_params() returned None. "
                    "PLC not connected or read error occurred. "
                    "Widgets will remain at default values."
                )
                self.statusbar.showMessage("PLC not connected — using default config.")
                self._check_and_show_connection_alert(False)
                return

            if not plc_cfg:
                print(
                    "[LOAD FROM PLC] FAILED: read_ui_params() returned an empty dict. "
                    "Widgets will remain at default values."
                )
                self.statusbar.showMessage("PLC returned empty data — using default config.")
                self._check_and_show_connection_alert(False)
                return

            print(f"[LOAD FROM PLC] Raw values received from PLC: {plc_cfg}")

            set_config_values(self, plc_cfg)

            VERIFY_MAP = {
                "steering_responsiveness": ("spinSteeringResp",         2),
                "steady_state_correction": ("spinSteadyState",          2),
                "damping_stability":       ("spinDamping",              2),
                "correction_limit":        ("spinCorrectionLimit",      1),
                "steering_center_offset":  ("spinSteeringCenterOffset", 1),
                "braking_latency_ms":      ("spinBrakingLatency",       0),
            }

            applied_count = 0
            for key, (widget_name, _decimals) in VERIFY_MAP.items():
                if key in plc_cfg:
                    widget = getattr(self, widget_name, None)
                    if widget:
                        print(
                            f"[LOAD FROM PLC]   {widget_name:30s} <- {plc_cfg[key]!s:>10}  "
                            f"(displayed: '{widget.text()}')"
                        )
                        applied_count += 1
                    else:
                        print(
                            f"[LOAD FROM PLC]   WARNING: widget '{widget_name}' "
                            f"not found in UI for key '{key}'."
                        )
                else:
                    print(
                        f"[LOAD FROM PLC]   INFO: key '{key}' not present in PLC data — "
                        f"widget '{widget_name}' kept at default."
                    )

            print(
                f"[LOAD FROM PLC] SUCCESS: {applied_count} of "
                f"{len(VERIFY_MAP)} parameters loaded from PLC."
            )
            self.statusbar.showMessage(
                f"Config loaded from PLC ({applied_count} parameters)."
            )
            self._check_and_show_connection_alert(True)

        except ConnectionError as e:
            print(f"[LOAD FROM PLC] CONNECTION ERROR: {e}")
            print(
                f"[LOAD FROM PLC] Check that the network cable is connected and "
                f"PLC IP ({self._forwarder.PLC_IP}) is reachable from this machine."
            )
            self.statusbar.showMessage(f"Failed to connect PLC ({self._forwarder.PLC_IP}) Please check cable")
            self._check_and_show_connection_alert(False)

        except ValueError as e:
            print(f"[LOAD FROM PLC] VALUE ERROR (invalid data from PLC): {e}")
            print(
                "[LOAD FROM PLC] A DM word may contain an out-of-range value "
                "or unexpected format."
            )
            self.statusbar.showMessage("Invalid PLC data — using default config.")
            self._check_and_show_connection_alert(False)

        except AttributeError as e:
            print(
                f"[LOAD FROM PLC] ATTRIBUTE ERROR: {e}  "
                "— widget may be missing from UI file (menu.ui)."
            )
            print(traceback.format_exc())
            self.statusbar.showMessage("Internal error while applying config — using defaults.")
            self._check_and_show_connection_alert(False)

        except Exception as e:
            print(f"[LOAD FROM PLC] UNEXPECTED ERROR ({type(e).__name__}): {e}")
            print(f"[LOAD FROM PLC] Traceback:\n{traceback.format_exc()}")
            self.statusbar.showMessage(
                f"Failed to load PLC config ({type(e).__name__}) — using defaults."
            )
            self._check_and_show_connection_alert(False)

    #  ALERT METHODS FOR PLC AND CAMERA
    def _check_and_show_connection_alert(self, plc_connected: bool):
        self._plc_connected = plc_connected
        self._refresh_alerts()

    def _check_and_show_camera_alert(self, camera_connected: bool):
        self._camera_connected = camera_connected
        self._refresh_alerts()

    def _refresh_alerts(self):
        plc_ok = self._plc_connected
        camera_ok = self._camera_connected
        
        # Handle PLC alert
        if hasattr(self, 'cardConnectionAlert'):
            if not plc_ok:
                if hasattr(self, 'txtCardMessage'):
                    self.txtCardMessage.setText(
                        "PLC tidak terhubung. Pastikan kabel jaringan terpasang "
                        "dan PLC dalam kondisi menyala."
                    )
                self.cardConnectionAlert.show()
                self.cardConnectionAlert.raise_()
            else:
                self.cardConnectionAlert.hide()
        
        # Handle Camera alert
        if hasattr(self, 'cardCameraAlert'):
            if not camera_ok:
                if hasattr(self, 'txtCameraCardMessage'):
                    self.txtCameraCardMessage.setText(
                        "Kamera tidak terdeteksi. Cek koneksi kabel dan pastikan "
                        "source video tersedia."
                    )
                self.cardCameraAlert.show()
                self.cardCameraAlert.raise_()
            else:
                self.cardCameraAlert.hide()
        
        # Update status bar message based on both conditions
        if not plc_ok and not camera_ok:
            self.statusbar.showMessage("⚠ PLC dan Kamera tidak terhubung")
        elif not plc_ok:
            self.statusbar.showMessage("⚠ PLC tidak terhubung — Kamera OK")
        elif not camera_ok:
            self.statusbar.showMessage("⚠ Kamera tidak terdeteksi — PLC OK")
        else:
            current_msg = self.statusbar.currentMessage()
            if "System Ready" not in current_msg:
                import torch
                device_info = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
                self.statusbar.showMessage(f"System Ready — ADAS [{device_info}] | PLC & Camera OK")

    def _initial_connection_check(self):
        self._load_config_from_plc()

    def _poll_plc_connection(self):
        def _worker():
            try:
                result = self._forwarder.read_ui_params()
                plc_ok = result is not None
            except Exception:
                plc_ok = False

            QTimer.singleShot(0, lambda: self._on_plc_poll_result(plc_ok))

        t = threading.Thread(target=_worker, daemon=True, name="plc-poll")
        t.start()

    def _on_plc_poll_result(self, plc_ok: bool):
        self._check_and_show_connection_alert(plc_ok)

    def _poll_camera_status(self):
        camera_ok = last_detect.get_camera_status()
        self._check_and_show_camera_alert(camera_ok)

    def _update_video_frame(self):
        if not last_detect.DISPLAY_ENABLED:
            return

        frame = last_detect.get_display_frame()
        if frame is None:
            return

        self._video_window.update_frame(frame)

    def _on_video_back(self):
        last_detect.disable_display()
        self._video_window.hide()
        self.show()
        self.raise_()
        self.btnStart.setChecked(False)
        self.statusbar.showMessage("ADAS detection running in background...")

    def _on_video_open_settings(self):
        QTimer.singleShot(0, self._show_main_and_open_config)

    def _show_main_and_open_config(self):
        last_detect.disable_display()
        self._video_window.hide()
        self.show()
        self.raise_()
        self.activateWindow()
        self.btnStart.setChecked(False)
        self.open_config_panel()
        self.statusbar.showMessage("Configuration panel opened from video.")

    def _start_detection_background(self):
        last_detect.start_detection()
        last_detect.set_status_callback(
            lambda msg: self.statusbar.showMessage(msg)
        )
        import torch
        device_info = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
        self.statusbar.showMessage(f"System Ready — ADAS [{device_info}]")

    def _sync_display_state(self):
        display_on = last_detect.DISPLAY_ENABLED
        if self.btnStart.isChecked() != display_on:
            self.btnStart.setChecked(display_on)
            if not display_on:
                self._video_window.hide()
                self.show()
                self.raise_()
                self.statusbar.showMessage("ADAS detection running in background...")

        thread_alive = (
            last_detect._detect_thread is not None and
            last_detect._detect_thread.is_alive()
        )
        if not thread_alive:
            print("[MAIN] Detection thread died, restarting...")
            self._start_detection_background()

    def toggle_display(self):
        if self.btnStart.isChecked():
            last_detect.enable_display()
            self._video_window.show()
            self._video_window.raise_()
            self.statusbar.showMessage("ADAS video display ON.")
            self.hide()
        else:
            last_detect.disable_display()
            self._video_window.hide()
            self.show()
            self.statusbar.showMessage("ADAS detection running in background...")

    def closeEvent(self, event):
        self._display_timer.stop()
        self._sync_timer.stop()
        if self._ignition_timer:
            self._ignition_timer.stop()
        self._plc_check_timer.stop()
        self._camera_check_timer.stop()
        last_detect.stop_detection()
        self._video_window.close()
        self._forwarder.disconnect()
        event.accept()

    #  PANEL – CONFIGURATION
    def toggle_config_panel(self):
        if self.panelConfiguration.isVisible():
            self.close_config_panel()
        else:
            if self.panelLaneLKA.isVisible():
                self._force_close_panel2()
            self.open_config_panel()

    def open_config_panel(self):
        panel = self.panelConfiguration
        self._anim_close.stop()
        panel.show()
        panel.raise_()
        self._raise_overlay_widgets()
        start = QRect(-panel.width(), panel.y(), panel.width(), panel.height())
        end   = QRect(20,             panel.y(), panel.width(), panel.height())
        self._anim_open.setStartValue(start)
        self._anim_open.setEndValue(end)
        self._anim_open.start()
        self.btnConfiguration.setChecked(True)
        self.statusbar.showMessage("Configuration panel opened.")

    def close_config_panel(self):
        panel = self.panelConfiguration
        self._anim_open.stop()
        start = panel.geometry()
        end   = QRect(-panel.width(), panel.y(), panel.width(), panel.height())
        self._anim_close.setStartValue(start)
        self._anim_close.setEndValue(end)
        self._anim_close.start()
        self.btnConfiguration.setChecked(False)
        self.statusbar.showMessage("System Ready...")

    def _force_close_panel2(self):
        self._anim_open2.stop()
        self._anim_close2.stop()
        self.panelLaneLKA.hide()
        self.btnLaneLKA.setChecked(False)

    def _on_panel_close_finished(self):
        self.panelConfiguration.hide()
        if self._active_info_key and self._active_info_key in self._info_buttons:
            self._info_buttons[self._active_info_key].setChecked(False)
        self._active_info_key = None
        self._show_adas_description()

    def save_config(self):
        cfg = get_config_values(self)
        print("[CONFIG SAVED]", cfg)

        plc_data = {
            "Kp":                     cfg["steering_responsiveness"],
            "Ki":                     cfg["steady_state_correction"],
            "Kd":                     cfg["damping_stability"],
            "Correction Limit":       cfg["correction_limit"],
            "Steering Center Offset": cfg["steering_center_offset"],
            "Brake Delay":            cfg["braking_latency_ms"],
        }

        try:
            self._forwarder.send_ui_params(plc_data) 
            self.statusbar.showMessage("Configuration saved & sent to PLC.")
        except Exception as e:
            print(f"[SAVE CONFIG] PLC send failed ({type(e).__name__}): {e}")
            self.statusbar.showMessage(
                f"Config saved locally, but failed to send to PLC ({type(e).__name__})."
            )

        existing  = load_settings() or {}
        lane_cfg  = existing.get("lane_lka", get_lane_lka_values(self))
        ok        = save_settings(cfg, lane_cfg)
        if ok:
            print("[SETTINGS] Config Hardware saved to file.")
        else:
            print("[SETTINGS] WARNING: Config Hardware gagal disimpan ke file.")
            
        self.close_config_panel()

    def reset_config(self):
        reset_config_values(self)
        self.statusbar.showMessage("Configuration reset to default.")

    #  PANEL – LANE DETECTION & LKA
    def toggle_lane_lka_panel(self):
        if self.panelLaneLKA.isVisible():
            self.close_lane_lka_panel()
        else:
            if self.panelConfiguration.isVisible():
                self._force_close_panel1()
            self.open_lane_lka_panel()

    def open_lane_lka_panel(self):
        panel = self.panelLaneLKA
        self._anim_close2.stop()
        panel.show()
        panel.raise_()
        self._raise_overlay_widgets()
        start = QRect(-panel.width(), panel.y(), panel.width(), panel.height())
        end   = QRect(20, panel.y(), panel.width(), panel.height())
        self._anim_open2.setStartValue(start)
        self._anim_open2.setEndValue(end)
        self._anim_open2.start()
        self.btnLaneLKA.setChecked(True)
        self.statusbar.showMessage("Lane Detection & LKA panel opened.")

    def close_lane_lka_panel(self):
        panel = self.panelLaneLKA
        self._anim_open2.stop()
        start = panel.geometry()
        end   = QRect(-panel.width(), panel.y(), panel.width(), panel.height())
        self._anim_close2.setStartValue(start)
        self._anim_close2.setEndValue(end)
        self._anim_close2.start()
        self.btnLaneLKA.setChecked(False)
        self.statusbar.showMessage("System Ready...")

    def _force_close_panel1(self):
        self._anim_open.stop()
        self._anim_close.stop()
        self.panelConfiguration.hide()
        self.btnConfiguration.setChecked(False)

    def _on_panel2_close_finished(self):
        self.panelLaneLKA.hide()
        if self._active_info_key and self._active_info_key in self._info_buttons:
            self._info_buttons[self._active_info_key].setChecked(False)
        self._active_info_key = None
        self._show_adas_description()

    def save_lane_lka(self):
        cfg = get_lane_lka_values(self)
        print("[LANE LKA SAVED]", cfg)

        if cfg["safety_max_steer_deg"] > cfg["max_steer_abs"]:
            self.statusbar.showMessage(
                "WARNING: Safety Max Steer > Max Steering Command — please review!"
            )
            return

        shared_config.update(cfg)
        print("[SHARED CONFIG UPDATED]", shared_config.get())

        existing = load_settings() or {}
        hw_cfg   = existing.get("config", get_config_values(self))
        ok       = save_settings(hw_cfg, cfg)
        if ok:
            print("[SETTINGS] Lane & LKA saved to file.")
            self.statusbar.showMessage("Lane & LKA settings saved to file & applied.")
        else:
            print("[SETTINGS] WARNING: Lane & LKA gagal disimpan ke file.")
            self.statusbar.showMessage("Lane & LKA settings applied (file save failed).")
        
        self.close_lane_lka_panel()

    def reset_lane_lka(self):
        reset_lane_lka_values(self)
        shared_config.reset()
        self.statusbar.showMessage("Lane Detection & LKA settings reset to default.")

    def _connect_info_buttons(self):
        for btn_name, spin_key in INFO_BTN_MAP.items():
            btn = getattr(self, btn_name, None)
            if btn:
                btn.clicked.connect(lambda checked, k=spin_key, b=btn_name: self._show_info(k, b))
                self._info_buttons[spin_key] = btn

        for btn_name, spin_key in INFO_BTN_MAP_LANE_LKA.items():
            btn = getattr(self, btn_name, None)
            if btn:
                btn.clicked.connect(lambda checked, k=spin_key, b=btn_name: self._show_info(k, b))
                if spin_key not in self._info_buttons:
                    self._info_buttons[spin_key] = btn

    def _setup_overlay_widgets(self):
        ov = self.labelOverlay_2
        ox, oy = ov.x(), ov.y()
        ow, oh = ov.width(), ov.height()
        px, py = 22, 18

        self._adas_title = QLabel(self.centralwidget)
        self._adas_title.setGeometry(ox + px, oy + py, ow - px * 2, 52)
        self._adas_title.setStyleSheet(
            "color: rgba(255,255,255,230); font-family: 'MS Shell Dlg 2';"
            "font-size: 13pt; font-weight: bold; background: transparent;"
        )
        self._adas_title.setText("Advanced Driver\nAssistance System")

        self._adas_divider = QLabel(self.centralwidget)
        self._adas_divider.setGeometry(ox + px, oy + py + 60, ow - px * 2, 1)
        self._adas_divider.setStyleSheet("background-color: rgba(255,255,255,50);")

        self._adas_body = QLabel(self.centralwidget)
        self._adas_body.setGeometry(ox + px, oy + py + 70, ow - px * 2, oh - py * 2 - 88)
        self._adas_body.setStyleSheet(
            "color: rgba(255,255,255,170); font-family: 'MS Shell Dlg 2';"
            "font-size: 9pt; background: transparent;"
        )
        self._adas_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._adas_body.setWordWrap(True)
        self._adas_body.setText(
            "Sistem ADAS Level 2 mengintegrasikan Lane\n"
            "Keeping Assist dan Automatic Emergency\n"
            "Braking secara bersamaan.\n\n"
            "Kamera mendeteksi marka jalan & obstacle\n"
            "secara real-time. Sistem mengambil alih\n"
            "kendali setir & rem jika diperlukan, namun\n"
            "pengemudi tetap harus siaga sepenuhnya.\n\n"
            "Buka Configuration untuk parameter\n"
            "utama, atau Lane & LKA untuk tuning\n"
            "deteksi jalur dan lane keeping."
        )

        self._adas_footer = QLabel(self.centralwidget)
        self._adas_footer.setGeometry(ox + px, oy + oh - py - 16, ow - px * 2, 14)
        self._adas_footer.setStyleSheet(
            "color: rgba(255,255,255,80); font-family: 'MS Shell Dlg 2';"
            "font-size: 7pt; background: transparent; letter-spacing: 1px;"
        )
        self._adas_footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._adas_footer.setText("TMMIN  ·  ASP-TECH")

        self._info_badge = QLabel(self.centralwidget)
        self._info_badge.setGeometry(ox + px, oy + py, ow - px * 2, 34)
        self._info_badge.setStyleSheet(
            "color: rgba(217,217,217,255); font-family: 'MS Shell Dlg 2';"
            "font-size: 28pt; font-weight: bold; background: transparent;"
        )
        self._info_badge.setText("DETAIL")

        self._info_divider = QLabel(self.centralwidget)
        self._info_divider.setGeometry(ox + px, oy + py + 42, ow - px * 2, 1)
        self._info_divider.setStyleSheet("background-color: rgba(255,255,255,50);")

        self._info_body = QLabel(self.centralwidget)
        self._info_body.setGeometry(
            ox + px, oy + py + 52,
            ow - px * 2, oh - py * 2 - 70
        )
        self._info_body.setStyleSheet(
            "color: rgba(255,255,255,185); font-family: 'MS Shell Dlg 2';"
            "font-size: 9pt; background: transparent;"
        )
        self._info_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._info_body.setWordWrap(True)
        self._info_body.setTextFormat(Qt.RichText)
        self._info_body.setText("")

        self._info_footer = QLabel(self.centralwidget)
        self._info_footer.setGeometry(ox + px, oy + oh - py - 16, ow - px * 2, 14)
        self._info_footer.setStyleSheet(
            "color: rgba(255,255,255,80); font-family: 'MS Shell Dlg 2';"
            "font-size: 7pt; background: transparent; letter-spacing: 1px;"
        )
        self._info_footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._info_footer.setText("TMMIN  ·  ASP-TECH")

        self._adas_widgets = [
            self._adas_title, self._adas_divider,
            self._adas_body, self._adas_footer,
        ]
        self._info_widgets = [
            self._info_badge, self._info_divider,
            self._info_body, self._info_footer,
        ]

    def _raise_overlay_widgets(self):
        for w in self._adas_widgets + self._info_widgets:
            w.raise_()

    def _show_adas_description(self):
        for w in self._info_widgets:
            w.hide()
        for w in self._adas_widgets:
            w.show()
            w.raise_()

    def _show_info(self, key: str, btn_name: str = None):
        if key not in INFO_TEXT:
            return
        title, body = INFO_TEXT[key]
        if self._active_info_key and self._active_info_key in self._info_buttons:
            self._info_buttons[self._active_info_key].setChecked(False)
        self._active_info_key = key
        self._info_buttons[key].setChecked(True)
        self._info_body.setText(body)
        for w in self._adas_widgets:
            w.hide()
        for w in self._info_widgets:
            w.show()
            w.raise_()
        self.statusbar.showMessage(f"Info: {title}")


if __name__ == "__main__":
    app    = QtWidgets.QApplication(sys.argv)
    _sound_filter = ClickSoundFilter(app)
    app.installEventFilter(_sound_filter)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())