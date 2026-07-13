from collections import defaultdict, Counter
import time


class BibMemory:


    def __init__(
        self,
        max_history=20,
        min_votes=3,
        expire_time=5
    ):

        self.max_history = max_history
        self.min_votes = min_votes
        self.expire_time = expire_time


        # penyimpanan data tiap atlet
        self.memory = {}



    def update(
        self,
        track_id,
        number,
        confidence
    ):
        now = time.time()


        # jika ID baru
        if track_id not in self.memory:

            self.memory[track_id] = {

                "numbers": [],

                "last_seen": now,

                "final": None
            }


        data = self.memory[track_id]


        data["last_seen"] = now


        # hanya simpan hasil valid
        if number is not None:

            data["numbers"].append(
                {
                    "value": number,
                    "confidence": confidence
                }
            )


        # batasi history
        if len(data["numbers"]) > self.max_history:

            data["numbers"] = data["numbers"][
                -self.max_history:
            ]


        # hitung hasil
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




    def cleanup(self):

        """
        Hapus atlet yang sudah hilang
        """

        now = time.time()


        remove = []


        for track_id, data in self.memory.items():

            if now - data["last_seen"] > self.expire_time:

                remove.append(track_id)



        for track_id in remove:

            del self.memory[track_id]