from dataclasses import dataclass
from typing import Optional
# from OCR.preprocess import ImagePreprocessor
from OCR.bib_validator import BibValidator
from OCR.paddle_engine import PaddleEngine
import cv2
@dataclass
class OCRResult:
    number: Optional[str] = None
    confidence: float = 0.0
    valid: bool = False
    processed_image = None
class BibOCR:
    def __init__(self):
        # self.preprocessor = ImagePreprocessor()
        self.engine = PaddleEngine()
        self.validator = BibValidator()

    def process(self, image):
        if image is None:
            return OCRResult()

        if image.size == 0:
            return OCRResult()

        # processed = self.preprocessor.process(image)        
        # text, confidence = self.engine.read(processed)
        text, confidence = self.engine.read(image)
        valid, clean_text = self.validator.validate(text)
        if valid:
            text = clean_text
        else:
            text = None

        result = OCRResult()
        result.number = text
        result.confidence = confidence
        result.valid = valid
        # result.processed_image = processed
        result.processed_image = image
        return result