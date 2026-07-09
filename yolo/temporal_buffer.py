from collections import deque
class TemporalBuffer:
    def __init__(self, max_frames=10): # max_frames: berapa frame yang disimpan
        self.max_frames = max_frames
        self.buffer = deque(maxlen=max_frames)

    def update(self, objects):
        self.buffer.append(objects)

    def get_stable_objects(self):
        class_map = {}

        for frame_objects in self.buffer:
            for obj in frame_objects:
                cls = obj['class']
                track_id = obj['track_id']

                if cls not in class_map:
                    class_map[cls] = {}

                if track_id not in class_map[cls]:
                    class_map[cls][track_id] = {
                        'count': 0,
                        'last_obj': obj
                    }

                class_map[cls][track_id]['count'] += 1
                class_map[cls][track_id]['last_obj'] = obj

        stable_objects = []

        for cls, tracks in class_map.items():
            best_track = max(tracks.values(), key=lambda x: x['count'])
            stable_objects.append(best_track['last_obj'])

        return stable_objects

class EgoLaneBuffer(TemporalBuffer):
    def __init__(self, max_frames=5, min_count=2):
        # panggil constructor parent class
        super().__init__(max_frames=max_frames)
        self.min_count = min_count

    def get_stable_target(self, lane_filter_func):
        filtered_buffer = []
        for frame_objects in self.buffer:
            filtered = [obj for obj in frame_objects if lane_filter_func(obj)]
            filtered_buffer.append(filtered)

        # hitung kemunculan tiap track_id
        track_map = {}
        for frame_objects in filtered_buffer:
            for obj in frame_objects:
                track_id = obj['track_id']
                if track_id not in track_map:
                    track_map[track_id] = {'count': 0, 'last_obj': obj}
                track_map[track_id]['count'] += 1
                track_map[track_id]['last_obj'] = obj

        # pilih object paling sering muncul
        stable_candidates = [v for v in track_map.values() if v['count'] >= self.min_count]
        if not stable_candidates:
            return None  # tidak ada object stabil
        best_track = max(stable_candidates, key=lambda x: x['count'])
        return best_track['last_obj']
