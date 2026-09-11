import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

# Ensure data directories exist
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
PREPROCESSED_DIR = DATA_DIR / "preprocessed"
REPORTS_DIR = DATA_DIR / "reports"
SAMPLES_DIR = DATA_DIR / "samples"

for directory in (DATA_DIR, UPLOAD_DIR, PREPROCESSED_DIR, REPORTS_DIR, SAMPLES_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Tesseract executable detection
DEFAULT_TESSERACT_PATHS = [
    os.getenv("TESSERACT_CMD"),
    r"C:\msys64\ucrt64\bin\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Users\devesh singh\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    "tesseract"
]

def get_tesseract_cmd() -> str:
    for path in DEFAULT_TESSERACT_PATHS:
        if path and (os.path.exists(path) or path == "tesseract"):
            return path
    return "tesseract"

TESSERACT_CMD = get_tesseract_cmd()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'labelcheck.db'}")

# Compliance Thresholds
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "65.0"))
LOW_QUALITY_THRESHOLD = float(os.getenv("LOW_QUALITY_THRESHOLD", "40.0"))
RULES_CONFIG_PATH = BASE_DIR / "rules" / "legal_metrology_2011.json"

# OCR Engine Configurations (Configurable via env vars)
TESSERACT_OEM = int(os.getenv("TESSERACT_OEM", "1"))  # 1 = LSTM neural net mode
TESSERACT_PSM_PRIMARY = int(os.getenv("TESSERACT_PSM_PRIMARY", "4"))  # 4 = single column of variable sizes, 6 = uniform block
TESSERACT_PSM_SPARSE = int(os.getenv("TESSERACT_PSM_SPARSE", "11"))  # 11 = sparse text, 12 = sparse text with OSD
# Disables dictionary-based auto-correction which causes hallucinatory character substitutions on codes/labels
TESSERACT_EXTRA_CONFIG = os.getenv("TESSERACT_EXTRA_CONFIG", "-c load_system_dawg=0 -c load_freq_dawg=0")

# Image Preprocessing & Dimension Caps
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "2200"))  # Downscale if larger
MIN_IMAGE_DIMENSION = int(os.getenv("MIN_IMAGE_DIMENSION", "1500"))  # Aggressive upscale if smaller to ensure 25-35px character height
DESKEW_MIN_ANGLE = float(os.getenv("DESKEW_MIN_ANGLE", "0.5"))  # Skip deskewing below this angle in degrees
DESKEW_MAX_ANGLE = float(os.getenv("DESKEW_MAX_ANGLE", "6.0"))  # Skip if angle seems to be package skew rather than text line
