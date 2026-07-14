from OCR.bib_ocr import BibOCR
from OCR.bib_memory import BibMemory
from OCR.ocr_worker import OCRWorker
from OCR.ocr_config import OCRConfig
import time
class BibManager:
    def __init__(self):
        self.ocr = BibOCR()
        self.memory = BibMemory()
        self.worker = OCRWorker(
            self.ocr,
            self.memory
        )
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
                return self.worker.get_result(track_id)
        
        self.last_process[track_id] = current
        self.worker.submit(track_id, image)

        return self.worker.get_result(track_id)

    def get(self, track_id):
        return self.memory.get(track_id)

    def cleanup(self):
        self.worker.stop()
        self.memory.cleanup()