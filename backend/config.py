import os
import shutil
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

# Server Binding
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# CORS Configuration
raw_cors = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

# Security & Auth
AUTH_SALT = os.getenv("AUTH_SALT", "labelcheck_salt_2026")

# Ensure data directories exist
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = DATA_DIR / "uploads"
PREPROCESSED_DIR = DATA_DIR / "preprocessed"
REPORTS_DIR = DATA_DIR / "reports"
SAMPLES_DIR = DATA_DIR / "samples"

for directory in (DATA_DIR, UPLOAD_DIR, PREPROCESSED_DIR, REPORTS_DIR, SAMPLES_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Tesseract executable detection (cross-platform Linux/Docker + Windows)
def get_tesseract_cmd() -> str:
    # 1. User-configured environment variable
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and (os.path.exists(env_cmd) or shutil.which(env_cmd)):
        return env_cmd

    # 2. System PATH check (standard on Linux / Docker containers)
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    # 3. Known Windows installations fallback
    windows_fallbacks = [
        r"C:\msys64\ucrt64\bin\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Users\devesh singh\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]
    for path in windows_fallbacks:
        if os.path.exists(path):
            return path

    return "tesseract"

TESSERACT_CMD = get_tesseract_cmd()

# Database URL with Postgres dialect normalization
raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'labelcheck.db'}")
if raw_db_url.startswith("postgres://"):
    # SQLAlchemy requires postgresql:// instead of postgres://
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = raw_db_url

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

# Image Preprocessing & Dimension Caps (Optimized for speed & accuracy on cloud vCPUs)
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "1600"))  # Downscale if larger to prevent bottlenecks
MIN_IMAGE_DIMENSION = int(os.getenv("MIN_IMAGE_DIMENSION", "1400"))  # Target 25-35px character height
DESKEW_MIN_ANGLE = float(os.getenv("DESKEW_MIN_ANGLE", "0.5"))  # Skip deskewing below this angle in degrees
DESKEW_MAX_ANGLE = float(os.getenv("DESKEW_MAX_ANGLE", "6.0"))  # Skip if angle seems to be package skew rather than text line
