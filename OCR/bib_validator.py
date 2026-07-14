import re
from OCR.ocr_config import OCRConfig
class BibValidator:
    def __init__(self):
        self.min_length = OCRConfig.MIN_DIGITS
        self.max_length = OCRConfig.MAX_DIGITS

    def clean(self, text):
        if text is None:
            return None
        
        text = str(text)
        text = text.strip()
        replacements = {

            "O": "0",
            "I": "1",
            "L": "1",
            "S": "5",
            "B": "8",
            "Z": "2"
        }

        for old, new in replacements.items():
            text = text.replace(
                old,
                new
            )

        return text

    def validate(self, text):
        text = self.clean(text)

        if text is None:
            return False, None

        if OCRConfig.ONLY_NUMERIC:
            if not text.isdigit():
                return False, None

        if len(text) < self.min_length:
            return False, None

        if len(text) > self.max_length:
            return False, None

        return True, text