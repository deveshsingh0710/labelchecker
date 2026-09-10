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
OCR_CONFIDENCE_THRESHOLD = 50.0  # Under 50% flags NEEDS_REVIEW if evaluation is uncertain
RULES_CONFIG_PATH = BASE_DIR / "rules" / "legal_metrology_2011.json"
