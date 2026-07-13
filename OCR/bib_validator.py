import re


class BibValidator:

    def __init__(
        self,
        min_length=3,
        max_length=6
    ):

        self.min_length = min_length
        self.max_length = max_length



    def clean(self, text):

        """
        Membersihkan hasil OCR
        """

        if text is None:
            return None


        text = str(text)


        # hapus spasi
        text = text.strip()


        # koreksi karakter OCR umum
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

        """
        Mengecek apakah bib valid
        """

        text = self.clean(text)


        if text is None:
            return False, None


        # harus angka semua
        if not text.isdigit():

            return False, None



        # cek panjang
        if len(text) < self.min_length:

            return False, None


        if len(text) > self.max_length:

            return False, None



        return True, text