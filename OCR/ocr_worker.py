import threading
import queue
import time

class OCRWorker:
    def __init__(self, bib_ocr, memory):
        self.bib_ocr = bib_ocr
        self.memory = memory
        self.pending = {}
        self.lock = threading.Lock()
        self.results = {}
        self.running = True
        self.thread = threading.Thread(
            target=self.run,
            daemon=True
        )
        self.thread.start()

    def submit(
        self,
        track_id,
        image
    ):
        if image is None:
            return
        with self.lock:
            self.pending[track_id] = image      

    def run(self):
        while self.running:
            try:
                track_id = None
                image = None
                
                with self.lock:
                    if self.pending:
                        track_id, image = self.pending.popitem()

                if image is None:
                    time.sleep(0.01)
                    continue

                result = self.bib_ocr.process(
                    image
                )

                if result.valid:
                    final_number = self.memory.update(
                        track_id,
                        result.number,
                        result.confidence
                    )
                    self.memory.update_best(
                        track_id,
                        result.number,
                        result.confidence
                    )
                    self.memory.reset_retry(track_id)
                else:
                    final_number = self.memory.get(track_id)
                    self.memory.increase_retry(track_id)

                self.memory.clear_processing(track_id)

                if final_number is not None:
                    self.memory.lock(track_id)

                self.results[track_id] = {
                    "ocr_number": result.number,
                    "confidence": result.confidence,
                    "final_number": final_number
                }

            except queue.Empty:
                continue

    def get_result(
        self,
        track_id
    ):
        return self.results.get(
            track_id,
            {
                "ocr_number": None,
                "confidence": 0.0,
                "final_number": self.memory.get(track_id)
            }
        )

    def stop(self):
        self.running = False