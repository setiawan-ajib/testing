import cv2
import numpy as np

from OCR.ocr_config import OCRConfig


class ImagePreprocessor:

    def __init__(self):
        pass

    def process(self, image):
        if image is None:
            return None

        if image.size == 0:
            return None

        img = image.copy()

        # ===================================
        # Resize
        # ===================================
        img = self.resize(img)

        # ===================================
        # Convert Gray
        # ===================================
        img = self.to_gray(img)

        # ===================================
        # CLAHE
        # ===================================
        if OCRConfig.APPLY_CLAHE:
            img = self.apply_clahe(img)

        # ===================================
        # Denoise
        # ===================================
        if OCRConfig.APPLY_DENOISE:
            img = self.denoise(img)

        # ===================================
        # Sharpen
        # ===================================
        if OCRConfig.APPLY_SHARPEN:
            img = self.sharpen(img)

        # ===================================
        # Threshold
        # ===================================
        if OCRConfig.APPLY_THRESHOLD:
            img = self.threshold(img)

        return img

    # =======================================================
    # Individual Processing
    # =======================================================

    def resize(self, image):

        target_width = OCRConfig.RESIZE_WIDTH

        if OCRConfig.KEEP_ASPECT_RATIO:

            h, w = image.shape[:2]

            if w == target_width:
                return image

            scale = target_width / w

            target_height = int(h * scale)

            return cv2.resize(
                image,
                (target_width, target_height),
                interpolation=cv2.INTER_CUBIC
            )

        else:

            return cv2.resize(
                image,
                (OCRConfig.RESIZE_WIDTH,
                 OCRConfig.RESIZE_WIDTH),
                interpolation=cv2.INTER_CUBIC
            )

    def to_gray(self, image):

        return cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    def apply_clahe(self, image):

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        return clahe.apply(image)

    def denoise(self, image):

        return cv2.fastNlMeansDenoising(
            image,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21
        )

    def sharpen(self, image):

        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])

        return cv2.filter2D(
            image,
            -1,
            kernel
        )

    def threshold(self, image):

        _, thresh = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        return thresh