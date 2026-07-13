import re
from typing import Optional, Tuple

from paddleocr import PaddleOCR

from OCR.ocr_config import OCRConfig


class PaddleEngine:

    def __init__(self):

        print("[OCR] Initializing PaddleOCR...")

        self.ocr = PaddleOCR(

            # CPU karena laptop tanpa GPU
            device="cpu",

            # Bahasa
            lang=OCRConfig.LANGUAGE,

            # PaddleOCR 3.x
            use_textline_orientation=True
        )

        print("[OCR] PaddleOCR ready")


    def read(
        self,
        image
    ) -> Tuple[Optional[str], float]:

        """
        Input:
            image = hasil preprocess

        Output:
            text, confidence
        """

        if image is None:
            return None, 0.0


        try:

            result = self.ocr.predict(image)


            best_text = None
            best_conf = 0.0


            for res in result:

                data = res.json


                if data is None:
                    continue


                # PaddleOCR 3.x result format
                rec_texts = data.get(
                    "rec_texts",
                    []
                )

                rec_scores = data.get(
                    "rec_scores",
                    []
                )


                for text, score in zip(
                    rec_texts,
                    rec_scores
                ):

                    # hanya ambil angka
                    number = re.sub(
                        r"\D",
                        "",
                        text
                    )


                    if number == "":
                        continue


                    score = float(score)


                    if score > best_conf:

                        best_conf = score
                        best_text = number



            return best_text, best_conf


        except Exception as e:

            print(
                "[OCR ERROR]",
                e
            )

            return None, 0.0