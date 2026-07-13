from dataclasses import dataclass
from typing import Optional

from OCR.preprocess import ImagePreprocessor
from OCR.paddle_engine import PaddleEngine


@dataclass
class OCRResult:
    number: Optional[str] = None

    confidence: float = 0.0

    valid: bool = False

    processed_image = None


class BibOCR:
    def __init__(self):

        self.preprocessor = ImagePreprocessor()
        self.engine = PaddleEngine()

    def process(self, image):
        if image is None:

            return OCRResult()

        if image.size == 0:

            return OCRResult()

        # =============================
        # Step 1
        # Preprocess
        # =============================

        processed = self.preprocessor.process(image)

        # =============================
        # Step 2
        # OCR
        # (sementara placeholder)
        # =============================

        # text = None

        # confidence = 0.0

        # valid = False

        text, confidence = self.engine.read(processed)
        valid = text is not None

        # =============================
        # Return
        # =============================

        result = OCRResult()

        result.number = text

        result.confidence = confidence

        result.valid = valid

        result.processed_image = processed

        return result