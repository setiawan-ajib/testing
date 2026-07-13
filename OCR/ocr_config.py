class OCRConfig:
    """
    OCR Global Configuration
    """

    # ===========================
    # PaddleOCR
    # ===========================
    USE_GPU = False

    LANGUAGE = "en"

    USE_ANGLE_CLASSIFIER = True

    # ===========================
    # OCR Processing
    # ===========================
    OCR_INTERVAL = 5
    """
    Jalankan OCR setiap N frame
    per Track ID.
    """

    MIN_CONFIDENCE = 0.70

    # ===========================
    # Image Preprocess
    # ===========================
    RESIZE_WIDTH = 320

    KEEP_ASPECT_RATIO = True

    APPLY_CLAHE = False

    APPLY_THRESHOLD = False

    APPLY_DENOISE = False

    APPLY_SHARPEN = False

    # ===========================
    # Bib Validation
    # ===========================
    MIN_DIGITS = 3

    MAX_DIGITS = 6

    ONLY_NUMERIC = True

    # ===========================
    # Memory
    # ===========================
    MEMORY_SIZE = 20

    LOCK_AFTER_SUCCESS = 5
    """
    Jika OCR membaca nomor yang sama
    sebanyak 5 kali,
    maka nomor dianggap final.
    """