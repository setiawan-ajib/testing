import cv2
from playsound3 import playsound
import numpy as np
import time
import threading


class ADASUI:
    def __init__(
        self,
        display_w,
        display_h,
        warning_logo=None,
        steer_left_icon=None,
        steer_right_icon=None,
        setting_icon=None,
        back_icon=None,
        ego_lane_icon=None,
        lane_colors=None
    ):
        self.DISPLAY_W = display_w
        self.DISPLAY_H = display_h

        self.WARNING_LOGO = warning_logo
        self.STEER_LEFT_ICON = steer_left_icon
        self.STEER_RIGHT_ICON = steer_right_icon
        self.SETTING_ICON = setting_icon
        self.BACK_ICON = back_icon
        self.EGO_LANE_ICON      = ego_lane_icon

        self.lane_colors = lane_colors or [
            (0, 0, 255),
            (0, 255, 0),
            (255, 0, 0),
            (0, 255, 255)
        ]

        self._btn_setting_rect = None   # (x1, y1, x2, y2)
        self._btn_back_rect    = None   # (x1, y1, x2, y2)
        self._btn_ego_toggle_rect = None
        self.last_warning_sound = 0
        self.warning_cooldown = 2.0 #detik

    # BASIC DRAWING UTILITIES
    def overlay_png(self, background, overlay, x, y):
        h, w = overlay.shape[:2]

        if x + w > background.shape[1] or y + h > background.shape[0]:
            return background

        if overlay.shape[2] == 4:
            alpha = overlay[:, :, 3] / 255.0
            for c in range(3):
                background[y:y+h, x:x+w, c] = (
                    alpha * overlay[:, :, c] +
                    (1 - alpha) * background[y:y+h, x:x+w, c]
                )
        else:
            background[y:y+h, x:x+w] = overlay

        return background

    def draw_rounded_rect(self, img, top_left, bottom_right, color, radius=30):
        x1, y1 = top_left
        x2, y2 = bottom_right

        overlay = img.copy()

        cv2.rectangle(overlay, (x1+radius, y1), (x2-radius, y2), color, -1)
        cv2.rectangle(overlay, (x1, y1+radius), (x2, y2-radius), color, -1)

        cv2.circle(overlay, (x1+radius, y1+radius), radius, color, -1)
        cv2.circle(overlay, (x2-radius, y1+radius), radius, color, -1)
        cv2.circle(overlay, (x1+radius, y2-radius), radius, color, -1)
        cv2.circle(overlay, (x2-radius, y2-radius), radius, color, -1)

        return overlay


    def _draw_icon_button(self, frame, icon, cx, cy, icon_size=32):
        btn_radius = icon_size // 2 + 10

        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), btn_radius, (255, 255, 255), -1)
        frame = cv2.addWeighted(overlay, 100 / 255.0, frame, 1 - (100 / 255.0), 0)

        if icon is not None:
            ico = icon.copy()
            ico = cv2.resize(ico, (icon_size, icon_size))
            ix = cx - icon_size // 2
            iy = cy - icon_size // 2
            frame = self.overlay_png(frame, ico, ix, iy)

        x1 = cx - btn_radius
        y1 = cy - btn_radius
        x2 = cx + btn_radius
        y2 = cy + btn_radius
        return frame, (x1, y1, x2, y2)

    def draw_overlay_buttons(self, frame):
        import last_detect_pc as lpc

        h, w = frame.shape[:2]

        icon_size = 32
        btn_radius = icon_size // 2 + 10
        margin = 16
        gap    = 12

        back_cx = w - margin - btn_radius
        back_cy = margin + btn_radius

        setting_cx = back_cx - (btn_radius * 2) - gap
        setting_cy = back_cy

        ego_cx     = setting_cx - (btn_radius * 2) - gap
        ego_cy     = back_cy

        frame, self._btn_setting_rect = self._draw_icon_button(
            frame, self.SETTING_ICON, setting_cx, setting_cy, icon_size
        )
        frame, self._btn_back_rect = self._draw_icon_button(
            frame, self.BACK_ICON, back_cx, back_cy, icon_size
        )

        bg_alpha = 100 if lpc.show_ego_lane_roi else 40
        overlay = frame.copy()
        cv2.circle(overlay, (ego_cx, ego_cy), btn_radius, (255, 255, 255), -1)
        frame = cv2.addWeighted(overlay, bg_alpha / 255.0, frame, 1 - (bg_alpha / 255.0), 0)

        if self.EGO_LANE_ICON is not None:
            ico = self.EGO_LANE_ICON.copy()
            ico = cv2.resize(ico, (icon_size, icon_size))

            if not lpc.show_ego_lane_roi:
                gray = cv2.cvtColor(ico[:, :, :3], cv2.COLOR_BGR2GRAY)
                gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                if ico.shape[2] == 4:
                    alpha_ch = ico[:, :, 3:4]
                    ico = np.concatenate([gray_bgr, alpha_ch], axis=2)
                else:
                    ico = gray_bgr

            ix = ego_cx - icon_size // 2
            iy = ego_cy - icon_size // 2
            frame = self.overlay_png(frame, ico, ix, iy)

        x1 = ego_cx - btn_radius
        y1 = ego_cy - btn_radius
        x2 = ego_cx + btn_radius
        y2 = ego_cy + btn_radius
        self._btn_ego_toggle_rect = (x1, y1, x2, y2)

        return frame

    def is_click_ego_toggle(self, x, y):
        if self._btn_ego_toggle_rect is None:
            return False
        x1, y1, x2, y2 = self._btn_ego_toggle_rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def is_click_setting(self, x, y):
        if self._btn_setting_rect is None:
            return False
        x1, y1, x2, y2 = self._btn_setting_rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def is_click_back(self, x, y):
        if self._btn_back_rect is None:
            return False
        x1, y1, x2, y2 = self._btn_back_rect
        return x1 <= x <= x2 and y1 <= y <= y2


    # POPUPS
    def draw_warning_popup(self, frame):
        self.playing_warning_sound()
        
        h, w = frame.shape[:2]
        
        popup_w, popup_h = 400, 140
        center_x = w // 2
        top_y = 30

        top_left = (center_x - popup_w // 2, top_y)
        bottom_right = (center_x + popup_w // 2, top_y + popup_h)

        overlay = frame.copy()

        overlay = self.draw_rounded_rect(
            overlay,
            top_left,
            bottom_right,
            (0, 255, 255),
            radius=35
        )

        frame = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)

        current_y = top_y + 15

        if self.WARNING_LOGO is not None:
            logo = self.WARNING_LOGO.copy()
            logo_width = 80
            scale_ratio = logo_width / logo.shape[1]
            logo_height = int(logo.shape[0] * scale_ratio)
            logo = cv2.resize(logo, (logo_width, logo_height))

            logo_x = center_x - logo_width // 2
            logo_y = current_y

            frame = self.overlay_png(frame, logo, logo_x, logo_y)
            current_y += logo_height + 15

        main_text = "WARNING VEHICLE AHEAD"
        font_scale = 0.8
        thickness = 2

        text_size = cv2.getTextSize(
            main_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            thickness
        )[0]

        text_x = center_x - text_size[0] // 2
        text_y = current_y + text_size[1]

        cv2.putText(
            frame,
            main_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 255),
            thickness
        )
        return frame

    def draw_danger_popup(self, frame):
        self.playing_danger_sound()
       
        h, w = frame.shape[:2]
        popup_w, popup_h = 420, 160
        center_x = w // 2
        top_y = 25
        top_left = (center_x - popup_w // 2, top_y)
        bottom_right = (center_x + popup_w // 2, top_y + popup_h)

        overlay = frame.copy()
        overlay = self.draw_rounded_rect(overlay, top_left, bottom_right, (0, 0, 220), radius=35)
        frame = cv2.addWeighted(overlay, 0.45, frame, 0.55, 0)

        current_y = top_y + 15
        if self.WARNING_LOGO is not None:
            logo = self.WARNING_LOGO.copy()
            logo_width = 90
            scale_ratio = logo_width / logo.shape[1]
            logo_height = int(logo.shape[0] * scale_ratio)
            logo = cv2.resize(logo, (logo_width, logo_height))
            logo_x = center_x - logo_width // 2
            logo_y = current_y
            frame = self.overlay_png(frame, logo, logo_x, logo_y)
            current_y += logo_height + 12

        main_text = "DANGER VEHICLE AHEAD"
        font_scale = 0.85
        thickness = 3
        text_size = cv2.getTextSize(main_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        
        text_x = center_x - text_size[0] // 2
        text_y = current_y + text_size[1] + 5

        cv2.putText(frame, main_text, (text_x+2, text_y+2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness+1)
        cv2.putText(frame, main_text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 220, 255), thickness)  # Kuning terang

        return frame

    def draw_steering_popup(self, frame, steering_deg):
        if steering_deg is None or steering_deg == -999 or abs(steering_deg) < 0.5:
            return frame

        h, w = frame.shape[:2]

        popup_w, popup_h = 300, 120
        center_x = w // 2
        bottom_y = h - 40

        top_left = (center_x - popup_w // 2, bottom_y - popup_h)
        bottom_right = (center_x + popup_w // 2, bottom_y)

        overlay = frame.copy()
        overlay = self.draw_rounded_rect(
            overlay,
            top_left,
            bottom_right,
            (128, 128, 128),
            radius=30
        )

        frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

        if steering_deg < 0:
            direction_text = "LEFT"
            icon = self.STEER_LEFT_ICON
        else:
            direction_text = "RIGHT"
            icon = self.STEER_RIGHT_ICON

        current_y = top_left[1] + 15

        if icon is not None:
            icon = icon.copy()
            icon_width = 70
            scale_ratio = icon_width / icon.shape[1]
            icon_height = int(icon.shape[0] * scale_ratio)
            icon = cv2.resize(icon, (icon_width, icon_height))

            icon_x = center_x - icon_width // 2
            icon_y = current_y

            frame = self.overlay_png(frame, icon, icon_x, icon_y)
            current_y += icon_height + 10

        font_scale = 0.8
        thickness = 2

        text_size = cv2.getTextSize(
            direction_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            thickness
        )[0]

        text_x = center_x - text_size[0] // 2
        text_y = current_y + text_size[1]

        cv2.putText(
            frame,
            direction_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            thickness
        )

        return frame

    def draw_info_popup(self, frame, steering_deg, brake_cmd, tracked_object, fps):
        h, w = frame.shape[:2]

        popup_w, popup_h = 250, 165
        margin = 20

        top_left = (margin, h - popup_h - margin)
        bottom_right = (margin + popup_w, h - margin)

        overlay = frame.copy()
        overlay = self.draw_rounded_rect(
            overlay,
            top_left,
            bottom_right,
            (0, 0, 0),
            radius=20
        )

        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        x_text = top_left[0] + 15
        y_text = top_left[1] + 30
        line_gap = 35

        steer_text = "Steering: No Lane" if steering_deg == -999 else f"Steering: {steering_deg:.1f} deg"
        brake_text = f"Brake: {'ON' if brake_cmd else 'OFF'}"
        track_text = f"Tracking: {'OK' if tracked_object else 'ERROR'}"
        fps_text = f"FPS: {fps:.1f}"

        cv2.putText(frame, steer_text, (x_text, y_text),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(frame, brake_text, (x_text, y_text + line_gap),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(frame, track_text, (x_text, y_text + 2*line_gap),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, fps_text, (x_text, y_text + 3*line_gap),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame

    # ROI & LANE
    def draw_roi_overlay(self, frame, roi_points, color=(0, 200, 200), alpha=0.25):
        if roi_points is None or len(roi_points) < 3:
            return frame

        overlay = frame.copy()
        roi_poly = np.array(roi_points, dtype=np.int32)

        cv2.fillPoly(overlay, [roi_poly], color)
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        return frame
    
    def draw_roi_warning(self, frame, roi_points, color=(255, 0, 0), alpha=0.25):
        if roi_points is None or len(roi_points) < 3:
            return frame

        overlay = frame.copy()
        roi_poly = np.array(roi_points, dtype=np.int32)

        cv2.fillPoly(overlay, [roi_poly], color)
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        return frame

    def draw_lanes(self, image, lanes_points, lanes_detected):
        vis_img = image.copy()

        for lane_num in [1, 2]:
            lane_points = lanes_points[lane_num]

            pts = [[int(x), int(y)] for x, y in lane_points]
            if len(pts) >= 2:
                cv2.polylines(
                    vis_img,
                    [np.array(pts, dtype=np.int32)],
                    isClosed=False,
                    color=self.lane_colors[lane_num],
                    thickness=2
                )

        return vis_img
    
    def draw_lanes_sliding(self, image, lane_data, transformer):
        left_fit = lane_data["left_fit"]
        right_fit = lane_data["right_fit"]

        if left_fit is None or right_fit is None:
            return image

        h, w = image.shape[:2]

        y_start = int(h * 0.45)
        y_end = h - 1

        ploty = np.linspace(y_start, y_end, y_end - y_start)

        left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
        right_fitx = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]

        lane_line_overlay = np.zeros_like(image)

        pts_left_draw = np.array([np.transpose(np.vstack([left_fitx, ploty]))], np.int32)
        pts_right_draw = np.array([np.transpose(np.vstack([right_fitx, ploty]))], np.int32)

        cv2.polylines(lane_line_overlay, pts_left_draw, isClosed=False, color=(0, 255, 0), thickness=5)
        cv2.polylines(lane_line_overlay, pts_right_draw, isClosed=False, color=(0, 255, 0), thickness=5)

        lane_line_unwarp = transformer.unwarp(lane_line_overlay)
        
        result = cv2.addWeighted(image, 1.0, lane_line_unwarp, 1.0, 0)

        return result
    
    # SOUND
    def playing_warning_sound(self):
        now = time.time()

        if now - self.last_warning_sound > self.warning_cooldown:
            self.last_warning_sound = now

            threading.Thread(
                target=playsound,
                args=("assets/data/sound/mixkit-emergency-alert-alarm-1007.wav",),
                daemon=True
            ).start()

    def playing_danger_sound(self):
        now = time.time()
        if now - self.last_warning_sound > self.warning_cooldown:
            self.last_warning_sound = now
            threading.Thread(
                target=playsound,
                args=("assets/data/sound/mixkit-classic-alarm-995.wav", ),
                daemon=True
            ).start()
    
    def draw_ego_lane_roi(self, frame, roi_points, lane_center_x=None, ego_center_x=None, color=(0, 255, 255), alpha=0.15):
        h, w = frame.shape[:2]
        cy = int(h * 0.8)
        
        if roi_points is not None and len(roi_points) > 2:
            overlay = frame.copy()
            pts = np.array(roi_points, dtype=np.int32)
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

        if lane_center_x is not None:
            x = int(lane_center_x)
            cv2.circle(frame, (x, cy), 6, (0, 255, 0), -1)
            cv2.putText(frame, "lane_center", (x + 5, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        if ego_center_x is not None:
            x = int(ego_center_x)
            cv2.circle(frame, (x, cy), 6, (0, 0, 255), -1)
            cv2.putText(frame, "ego_center", (x + 5, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return frame