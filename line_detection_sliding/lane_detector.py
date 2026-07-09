import cv2
import numpy as np
from line_detection_sliding.perspective import PerspectiveTransformer
from yolo.target_vehicle_selector import get_ego_lane_roi

class LaneDetector:
    def __init__(self):
        self.nwindows = 8
        self.margin = 70
        self.minpix = 120
        self.transformer = None
        self.left_fit_prev = None
        self.right_fit_prev = None


    def process(self, frame):
        if self.transformer is None:
            h, w = frame.shape[:2]
            self.transformer = PerspectiveTransformer((w, h))

        binary = self.preprocess(frame)
        binary_roi, roi_debug = self.region_of_interest(
            binary,
            frame=frame,
            debug=True)
        #cv2.imshow("ROI Debug", roi_debug)
        warped = self.transformer.warp(binary_roi)
        
        lane_data = self.sliding_window(warped, frame, warped.shape[:2])
        return lane_data

    def preprocess(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        blur = cv2.GaussianBlur(gray, (7, 7), 0)

        sobelx = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        abs_sobelx = np.absolute(sobelx)
        scaled = np.uint8(255 * abs_sobelx / np.max(abs_sobelx))

        _, binary = cv2.threshold(scaled, 50, 255, cv2.THRESH_BINARY)
        return binary

    def region_of_interest(self, img, frame=None, debug=False):
        h, w = img.shape[:2]

        mask = np.zeros_like(img)

        # ROI trapezoid (jalan)
        polygon = np.array([get_ego_lane_roi(w, h)], np.int32)

        cv2.fillPoly(mask, polygon, 255)

        if debug:
            debug_img = frame.copy()
            cv2.polylines(debug_img, polygon, True, (0, 255, 255), 3)
            return cv2.bitwise_and(img, mask), debug_img

        return cv2.bitwise_and(img, mask)
    
    def remove_outlier(self, x, y):
        mean = np.mean(x)
        std = np.std(x)

        mask = np.abs(x - mean) < 2 * std
        return x[mask], y[mask]
    

    def sliding_window(self, binary_warped, original, warped_shape):
        histogram = np.sum(binary_warped[binary_warped.shape[0]//2:, :], axis=0)

        histogram = histogram.astype(np.float32)
        histogram = cv2.GaussianBlur(histogram, (51, 1), 0)
        histogram[histogram < 50] = 0
        
        midpoint = histogram.shape[0] // 2
        leftx_base = np.argmax(histogram[:midpoint])
        rightx_base = np.argmax(histogram[midpoint:]) + midpoint

        window_height = binary_warped.shape[0] // self.nwindows
        nonzero = binary_warped.nonzero()
        nonzeroy = np.array(nonzero[0])
        nonzerox = np.array(nonzero[1])

        leftx_current = leftx_base
        rightx_current = rightx_base

        left_lane_inds = []
        right_lane_inds = []

        for window in range(self.nwindows):
            win_y_low = binary_warped.shape[0] - (window + 1) * window_height
            win_y_high = binary_warped.shape[0] - window * window_height

            win_xleft_low = leftx_current - self.margin
            win_xleft_high = leftx_current + self.margin
            win_xright_low = rightx_current - self.margin
            win_xright_high = rightx_current + self.margin

            good_left_inds = (
                (nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)
            ).nonzero()[0]

            good_right_inds = (
                (nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)
            ).nonzero()[0]

            left_lane_inds.append(good_left_inds)
            right_lane_inds.append(good_right_inds)

            if len(good_left_inds) > self.minpix:
                leftx_current = int(np.mean(nonzerox[good_left_inds]))
            if len(good_right_inds) > self.minpix:
                rightx_current = int(np.mean(nonzerox[good_right_inds]))

        left_lane_inds = np.concatenate(left_lane_inds)
        right_lane_inds = np.concatenate(right_lane_inds)

        leftx = nonzerox[left_lane_inds]
        lefty = nonzeroy[left_lane_inds]
        rightx = nonzerox[right_lane_inds]
        righty = nonzeroy[right_lane_inds]

        leftx, lefty = self.remove_outlier(leftx, lefty)
        rightx, righty = self.remove_outlier(rightx, righty)

        # ===============================
        # FIT POLYNOMIAL (SAFE)
        # ===============================
        fit_error = None

        if len(leftx) < 100 or len(rightx) < 100:
            if self.left_fit_prev is not None:
                return {
                    "left_fit": self.left_fit_prev,
                    "right_fit": self.right_fit_prev,
                    "fit_error": None
                }
            else:
                return {
                    "left_fit": None,
                    "right_fit": None,
                    "fit_error": None
                }
        
        else:
            left_fit = np.polyfit(lefty, leftx, 2)
            right_fit = np.polyfit(righty, rightx, 2)

        prev_left = self.left_fit_prev
        prev_right = self.right_fit_prev

        # ===============================
        # FIT ERROR (ROBUST VERSION)
        # ===============================
        try:
            # sampling (boleh, tapi jangan terlalu agresif)
            step = 2
            leftx_s = leftx[::step]
            lefty_s = lefty[::step]
            rightx_s = rightx[::step]
            righty_s = righty[::step]

            left_pred = left_fit[0]*lefty_s**2 + left_fit[1]*lefty_s + left_fit[2]
            right_pred = right_fit[0]*righty_s**2 + right_fit[1]*righty_s + right_fit[2]

            # 🔥 pakai median (lebih tahan noise)
            left_error = np.median(np.abs(leftx_s - left_pred))
            right_error = np.median(np.abs(rightx_s - right_pred))

            fit_error = (left_error + right_error) / 2

            # 🔥 WAJIB: normalisasi
            img_w = binary_warped.shape[1]
            fit_error = fit_error / img_w

        except Exception:
            fit_error = None

        # ===============================
        # LIMIT SHIFT
        # ===============================
        max_shift = 50

        if prev_left is not None and prev_right is not None:

            if abs(left_fit[2] - prev_left[2]) > max_shift:
                left_fit = prev_left.copy()

            if abs(right_fit[2] - prev_right[2]) > max_shift:
                right_fit = prev_right.copy()

        # ===============================
        # SMOOTHING (EMA)
        # ===============================
        if prev_left is None:
            self.left_fit_prev = left_fit
            self.right_fit_prev = right_fit
        else:
            alpha = 0.15
            left_fit = (1 - alpha) * prev_left + alpha * left_fit
            right_fit = (1 - alpha) * prev_right + alpha * right_fit

            self.left_fit_prev = left_fit
            self.right_fit_prev = right_fit
        
        lane_data = {
            "left_fit": left_fit,
            "right_fit": right_fit,
            "fit_error": fit_error
        }

        return lane_data