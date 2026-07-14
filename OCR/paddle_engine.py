import re
from typing import Optional, Tuple
from paddleocr import PaddleOCR
from OCR.ocr_config import OCRConfig
class PaddleEngine:
    def __init__(self):
        print("[OCR] Initializing PaddleOCR...")
        self.ocr = PaddleOCR(
            device="cpu",
            lang=OCRConfig.LANGUAGE,
            use_textline_orientation=OCRConfig.USE_TEXTLINE_ORIENTATION,
            use_doc_orientation_classify=OCRConfig.USE_DOC_ORIENTATION_CLASSIFY,
            use_doc_unwarping=OCRConfig.USE_DOC_UNWARPING
        )
        print("[OCR] PaddleOCR ready")

    def read(
        self,
        image
    ) -> Tuple[Optional[str], float]:

        if image is None:
            return None, 0.0
        
        # print(
        #     "[OCR INPUT SIZE]",
        #     image.shape
        # )

        try:
            result = self.ocr.predict(image)
            # print(result)
            best_text = None
            best_conf = 0.0

            for res in result:
                data = res.json

                if data is None:
                    continue

                if "res" in data:
                    data = data["res"]

                # print(
                #     "[OCR DATA KEYS]",
                #     data.keys()
                # )
                
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

                    number = re.sub(
                        r"\D",
                        "",
                        text
                    )

                    if number == "":
                        continue

                    score = float(score)

                    if score < OCRConfig.MIN_CONFIDENCE:
                        continue

                    if score > best_conf:
                        best_conf = score
                        best_text = number

            return best_text, best_conf

        except Exception as e:

            import traceback

            print("================ OCR ERROR ================")
            traceback.print_exc()
            print("===========================================")

            return None, 0.0