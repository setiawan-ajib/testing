from collections import defaultdict, Counter
import time
from OCR.ocr_config import OCRConfig
class BibMemory:
    def __init__(self):
        self.max_history = OCRConfig.MEMORY_SIZE
        self.min_votes = OCRConfig.LOCK_AFTER_SUCCESS
        self.expire_time = OCRConfig.MEMORY_EXPIRE_TIME
        self.memory = {}

    def update(
        self,
        track_id,
        number,
        confidence
    ):
        now = time.time()
        if track_id not in self.memory:
            self.memory[track_id] = {
                "numbers": [],
                "last_seen": now,
                "final": None,
                "locked": False,
                "processing": False,
                "best_number": None,
                "best_confidence": 0.0,
                "retry_count": 0,
                "last_ocr_frame": -1
            }

        data = self.memory[track_id]
        data["last_seen"] = now

        if number is not None:
            data["numbers"].append(
                {
                    "value": number,
                    "confidence": confidence
                }
            )

        if len(data["numbers"]) > self.max_history:
            data["numbers"] = data["numbers"][
                -self.max_history:
            ]

        data["final"] = self._vote(
            data["numbers"]
        )

        return data["final"]

    def _vote(
        self,
        history
    ):
        if len(history) < self.min_votes:
            return None

        values = []

        for item in history:
            values.append(
                item["value"]
            )

        counter = Counter(values)
        result, count = counter.most_common(1)[0]

        if count >= self.min_votes:
            return result
        return None

    def get(
        self,
        track_id
    ):
        if track_id in self.memory:
            return self.memory[track_id]["final"]
        return None
    
    def exist(self, track_id):
        return track_id in self.memory
    
    def get_state(self, track_id):
        return self.memory.get(track_id)
    
    def is_locked(self, track_id):
        if track_id not in self.memory:
            return False
        return self.memory[track_id]["locked"]
    
    def lock(self, track_id):
        if track_id in self.memory:
            self.memory[track_id]["locked"] = True
    
    def set_last_ocr_frame(self, track_id, frame_id):
        if track_id in self.memory:
            self.memory[track_id]["last_ocr_frame"] = frame_id
    
    def get_last_ocr_frame(self, track_id):
        if track_id not in self.memory:
            return -1
        return self.memory[track_id]["last_ocr_frame"]
    
    def increase_retry(self, track_id):
        if track_id in self.memory:
            self.memory[track_id]["retry_count"] += 1
    
    def reset_retry(self, track_id):
        if track_id in self.memory:
            self.memory[track_id]["retry_count"] = 0

    def get_retry(self, track_id):
        if track_id not in self.memory:
            return 0
        return self.memory[track_id]["retry_count"]
    
    def update_best(self, track_id, number, confidence):
        if track_id not in self.memory:
            return
        
        data = self.memory[track_id]

        if confidence > data["best_confidence"]:
            data["best_confidence"] = confidence
            data["best_number"] = number
    
    def get_best(self, track_id):
        if track_id not in self.memory:
            return None, 0.0
        
        data = self.memory[track_id]

        return (
            data["best_number"],
            data["best_confidence"]
        )
    
    def is_processing(self, track_id):
        if track_id not in self.memory:
            return False
        return self.memory[track_id]["processing"]
    
    def set_processing(self, track_id):
        if track_id in self.memory:
            self.memory[track_id]["processing"] = True
        
    def clear_processing(self, track_id):
        if track_id in self.memory:
            self.memory[track_id]["processing"] = False

    def cleanup(self):
        now = time.time()
        remove = []
        for track_id, data in self.memory.items():
            if now - data["last_seen"] > self.expire_time:
                remove.append(track_id)

        for track_id in remove:
            del self.memory[track_id]