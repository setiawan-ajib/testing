from OCR.bib_ocr import BibOCR
from OCR.bib_memory import BibMemory
from OCR.ocr_config import OCRConfig
import time
class BibManager:
    def __init__(self):
        self.ocr = BibOCR()
        self.memory = BibMemory()
        self.last_process = {}
        self.ocr_interval = OCRConfig.OCR_INTERVAL

    def update(
        self,
        track_id,
        image,
        frame_id=0
    ):
        
        current = frame_id
        if track_id in self.last_process:
            diff = current - self.last_process[track_id]
            if diff < self.ocr_interval:
                return {
                    "track_id": track_id,
                    "ocr_number": None,
                    "confidence": 0.0,
                    "final_number": self.memory.get(track_id)
                }
        
        self.last_process[track_id] = current
        result = self.ocr.process(image)
        final_number = None

        if result.valid:
            final_number = self.memory.update(
                track_id,
                result.number,
                result.confidence
            )

        return {
            "track_id": track_id,
            "ocr_number": result.number,
            "confidence": result.confidence,
            "final_number": final_number
        }

    def get(self, track_id):
        return self.memory.get(track_id)

    def cleanup(self):
        self.memory.cleanup()