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
        # self.last_process = {}
        # self.ocr_interval = OCRConfig.OCR_INTERVAL
        self.retry_interval = OCRConfig.OCR_RETRY_FRAME
        self.max_retry = OCRConfig.MAX_RETRY

    def update(
        self,
        track_id,
        image,
        frame_id=0
    ):
        if not self.memory.exist(track_id):
            self.memory.update(
                track_id,
                None,
                0.0
            )
        
        result = self.worker.get_result(track_id)

        if self.memory.is_locked(track_id):
            return result
        
        if self.memory.is_processing(track_id):
            return result
        
        if self.memory.get_retry(track_id) > self.max_retry:
            return result
        
        last_ocr = self.memory.get_last_ocr_frame(track_id)

        if last_ocr >= 0:
            diff = frame_id - last_ocr

            if diff < self.retry_interval:
                return result
        
        self.memory.set_processing(track_id)
        self.memory.set_last_ocr_frame(track_id, frame_id)
        self.worker.submit(track_id, image)

        return result

        # current = frame_id
        # if track_id in self.last_process:
        #     diff = current - self.last_process[track_id]
        #     if diff < self.ocr_interval:
        #         return self.worker.get_result(track_id)
        
        # self.last_process[track_id] = current
        # self.worker.submit(track_id, image)

        # return self.worker.get_result(track_id)

    def get(self, track_id):
        return self.memory.get(track_id)

    def cleanup(self):
        self.worker.stop()
        self.memory.cleanup()