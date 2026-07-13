from OCR.bib_ocr import BibOCR
from OCR.bib_memory import BibMemory



class BibManager:


    def __init__(self):

        self.ocr = BibOCR()

        self.memory = BibMemory()



    def update(
        self,
        track_id,
        image
    ):

        """
        Memproses satu crop bib
        """

        result = self.ocr.process(
            image
        )


        final_number = None


        if result.valid:

            final_number = self.memory.update(
                track_id,
                result.number,
                result.confidence
            )


        return {

            "track_id": track_id,

            "ocr_number": result.number,

            "confidence": result.confidence,

            "final_number": final_number

        }



    def get(
        self,
        track_id
    ):

        return self.memory.get(
            track_id
        )


    def cleanup(self):

        self.memory.cleanup()