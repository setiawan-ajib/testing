class TemporalLaneSmoother:
    def __init__(self, alpha=0.7, max_lanes=4):
        self.alpha = alpha
        self.max_lanes = max_lanes
        self.prev_lanes = [None] * max_lanes
        self.missing_counts = [0] * max_lanes
        self.max_missing = 3

    def smooth(self, lanes_points, lanes_detected):
        smoothed_lanes = []

        for lane_idx in range(self.max_lanes):
            curr_lane = lanes_points[lane_idx] if lanes_detected[lane_idx] else None
            prev_lane = self.prev_lanes[lane_idx]

            if curr_lane is None:
                self.missing_counts[lane_idx] += 1

                if self.missing_counts[lane_idx] > self.max_missing:
                    self.prev_lanes[lane_idx] = None
                    smoothed_lanes.append(None)
                else:
                    smoothed_lanes.append(prev_lane)
                
                continue
            
            self.missing_counts[lane_idx] = 0

            if prev_lane is None:
                smoothed_lanes.append(curr_lane)
                self.prev_lanes[lane_idx] = curr_lane
                continue

            smoothed_lane = []
            len_prev = len(prev_lane)
            len_curr = len(curr_lane)
            max_len = max(len_prev, len_curr)

            for i in range(max_len):
                x_prev, y_prev = prev_lane[i] if i < len_prev else prev_lane[-1]
                x_curr, y_curr = curr_lane[i] if i < len_curr else curr_lane[-1]

                x = int(self.alpha * x_prev + (1 - self.alpha) * x_curr)
                y = int(self.alpha * y_prev + (1 - self.alpha) * y_curr)

                smoothed_lane.append([x, y])

            self.prev_lanes[lane_idx] = smoothed_lane
            smoothed_lanes.append(smoothed_lane)


        return smoothed_lanes
