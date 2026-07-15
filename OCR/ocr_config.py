class OCRConfig:
    # ===========================
    # PaddleOCR
    # ===========================
    USE_GPU = False
    LANGUAGE = "en"
    USE_ANGLE_CLASSIFIER = False
    USE_TEXTLINE_ORIENTATION = False
    USE_DOC_ORIENTATION_CLASSIFY = False
    USE_DOC_UNWARPING = False
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
    MEMORY_EXPIRE_TIME = 5
    OCR_RETRY_FRAME = 15
    MAX_RETRY = 5

    # ===========================
    # OCR Manager
    # ===========================
    # OCR_INTERVAL = 10
