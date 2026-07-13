class OCRConfig:
    # ===========================
    # PaddleOCR
    # ===========================
    USE_GPU = False
    LANGUAGE = "en"
    USE_ANGLE_CLASSIFIER = False

    # ===========================
    # OCR Processing
    # ===========================
    OCR_INTERVAL = 5
    MIN_CONFIDENCE = 0.50

    # ===========================
    # Image Preprocess
    # ===========================
    RESIZE_WIDTH = 640
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
