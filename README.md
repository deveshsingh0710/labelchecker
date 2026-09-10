# LabelCheck — Packaged Commodity Compliance Checker

**LabelCheck** is an AI-powered compliance verification web application that inspects packaged commodity product labels against **India's Legal Metrology (Packaged Commodities) Rules, 2011**.

Users upload a photo of a packaged product or label. The system runs an OpenCV preprocessing pipeline (auto-deskew, glare reduction, contrast enhancement, and denoising), extracts key label fields via OCR with confidence metrics, runs them through a declarative rule-based compliance engine, visually maps each declaration using interactive color-coded bounding-box overlays, and generates inspector-ready PDF compliance audit reports.

---

## Key Features

- **OpenCV Image Preprocessing Pipeline**:
  - **Auto-Deskew**: Automatically detects text alignment skew using contour analysis and corrects rotation.
  - **Glare Reduction & Illumination Equalization**: Uses CLAHE on the luminance channel in LAB color space to handle reflections.
  - **Edge-Preserving Denoising**: Bilateral filtering to smooth paper texture without blurring text edges.
  - **Contrast & Sharpness Enhancement**: Unsharp masking to improve character edge definitions.
  - **Interactive Preprocessing Preview**: Allows users to compare the original upload and preprocessed image side-by-side or toggled before verification.

- **Modular OCR Architecture**:
  - Built with a clean `BaseOCREngine` abstraction.
  - Ships with **Tesseract OCR 5** (`pytesseract`) as the local baseline.
  - Designed for drop-in cloud OCR adapters (Google Cloud Vision, AWS Textract, Azure AI Vision).

- **Rule-Based Compliance Engine**:
  - Declarative external JSON rule configuration (`backend/rules/legal_metrology_2011.json`).
  - No hardcoded compliance rules.
  - Evaluates each mandatory declaration:
    - **Rule 6(1)(a)**: Name and complete address of Manufacturer / Packer / Importer.
    - **Rule 6(1)(b)**: Generic / Common name of the commodity.
    - **Rule 6(1)(c)**: Net quantity with standard SI units (`g`, `kg`, `ml`, `l`, `m`, `cm`, `N`). Detects illegal non-standard units (e.g. `gms`, `kilos`, `ltrs`).
    - **Rule 6(1)(d)**: Month and year of manufacture, packing, or import (`MM/YYYY` or `Month YYYY`).
    - **Rule 6(1)(e)**: Maximum Retail Price (MRP) in Rupees with explicit **"inclusive of all taxes"** qualifier.
    - **Rule 6(1)(f)**: Best-before or expiry date for commodities that may become unfit for consumption.
    - **Rule 6(1)(g)**: Consumer grievance redressal contact (toll-free phone, email, or physical address).
    - **Rule 6(1)(n)**: Country of origin declaration for imported commodities.
  - **Three-State Rule Evaluation**:
    - `PASS`: Compliant declaration meeting statutory formats.
    - `FAIL`: Clear absence or violation of statutory requirements.
    - `NEEDS_REVIEW`: Triggered when OCR confidence is low (< 50%) or optional/conditional — prevents false negative hard-fails on blurry pictures.
  - **Weighted Compliance Scoring**: Critical declarations (MRP, Net Qty, Manufacturer, Consumer Care) are heavily weighted to reflect real-world regulatory inspection priorities.

- **Interactive Results Page**:
  - Circular compliance score gauge with threshold indicator (`Compliant` ≥ 85%, `Partially Compliant` 60–84%, `Non-Compliant` < 60%).
  - Image canvas with color-coded bounding boxes:
    - 🟢 **Emerald**: Passed
    - 🔴 **Rose**: Violation / Non-Compliant
    - 🟡 **Amber**: Needs Review
  - Bidirectional hover/click sync between bounding boxes and rule items.
  - Detailed violation cards with legal references, plain-English explanations, and required remediation steps.

- **Audit-Ready PDF Report Generation**:
  - 1-click download of PDF audit reports generated via **ReportLab**.
  - Includes inspection metadata, overall score, annotated visual evidence with bounding boxes, complete statutory findings table, remediation instructions, and legal disclaimer.

- **Audit History Dashboard**:
  - SQLite database (via SQLAlchemy) logging all checks with thumbnails, scores, status, and direct PDF download links.

- **Built-In Demo Sample Labels**:
  - 1-click test buttons for **Compliant Snack Label**, **Non-Compliant Cookies Label**, and **Imported Chocolate Label**.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Tailwind CSS, Lucide React, Axios, Vite |
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| **Image Preprocessing** | OpenCV (`cv2`), NumPy, Pillow |
| **OCR Engine** | Tesseract OCR 5 (`pytesseract`), Modular `BaseOCREngine` |
| **PDF Generation** | ReportLab |
| **Database** | SQLite (SQLAlchemy ORM, ready for PostgreSQL migration) |

---

## Project Structure

```
Complaince Checker/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py                 # FastAPI router, endpoints & static file serving
│   ├── compliance/
│   │   ├── __init__.py
│   │   └── engine.py               # Generic rule evaluator & weighted scoring
│   ├── data/
│   │   ├── preprocessed/           # OpenCV enhanced images
│   │   ├── reports/                # Generated PDF audit reports
│   │   ├── samples/                # Built-in sample test labels
│   │   ├── uploads/                # Raw uploaded photos
│   │   └── labelcheck.db           # SQLite database
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseOCREngine, BoundingBox & OCRResult interfaces
│   │   ├── field_parser.py         # Legal Metrology regex & entity extractor
│   │   └── tesseract_engine.py     # Tesseract OCR engine implementation
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   └── pipeline.py             # OpenCV auto-deskew, CLAHE, denoise, sharpening
│   ├── reports/
│   │   ├── __init__.py
│   │   └── pdf_generator.py        # ReportLab PDF report compiler
│   ├── rules/
│   │   └── legal_metrology_2011.json # Declarative ruleset
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_parser.py          # Unit tests for regex & field parser
│   │   └── test_rules.py           # Unit tests for rule engine & weighted score
│   ├── config.py                   # Central paths, Tesseract detection, constants
│   ├── database.py                 # SQLAlchemy models & session
│   ├── generate_samples.py         # Script to regenerate sample test labels
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── BoundingBoxOverlay.tsx
│   │   │   ├── HistoryDashboard.tsx
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── LegalGuideModal.tsx
│   │   │   ├── Navbar.tsx
│   │   │   ├── PreprocessingPreview.tsx
│   │   │   ├── ScoreBadge.tsx
│   │   │   └── ViolationsList.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   └── types.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── README.md
```

---

## Local Setup & Installation

### Prerequisites

1. **Python 3.10+** (Tested on Python 3.11)
2. **Node.js 18+** (Tested on Node.js 24 LTS)
3. **Tesseract OCR 5**:
   - **Windows**:
     - Install via winget or MSYS2: `pacman -S mingw-w64-ucrt-x86_64-tesseract-ocr mingw-w64-ucrt-x86_64-tesseract-data-eng`
     - Or download the official installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and install to `C:\Program Files\Tesseract-OCR`.
     - Add Tesseract to your PATH or set the `TESSERACT_CMD` environment variable.
   - **macOS**: `brew install tesseract`
   - **Linux (Ubuntu/Debian)**: `sudo apt-get install tesseract-ocr tesseract-ocr-eng`

---

### Step 1: Backend Setup

1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Generate the test sample labels:
   ```bash
   python generate_samples.py
   ```

4. Run unit tests to verify rules and OCR parser:
   ```bash
   python -c "import sys; sys.path.insert(0, '.'); import tests.test_rules as tr; tr.test_rules_loading(); tr.test_compliant_evaluation(); tr.test_non_compliant_evaluation(); tr.test_low_confidence_triggers_needs_review(); import tests.test_parser as tp; tp.test_field_parser_regex(); print('All tests passed!')"
   ```

5. Start the FastAPI server:
   ```bash
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend API will be available at `http://127.0.0.1:8000`. Interactive Swagger documentation is at `http://127.0.0.1:8000/docs`.

---

### Step 2: Frontend Setup

1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install npm dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The application will be live at `http://localhost:5173`.

---

## How to Test the Application

1. Open `http://localhost:5173` in your browser.
2. In the **Verifier** tab:
   - Click one of the pre-built sample labels (e.g. **Test Compliant Label** or **Test Violations Label**).
   - Alternatively, drag and drop any image of a packaged commodity product.
3. Observe **Step 1: OpenCV Preprocessing**:
   - Compare the raw image with the preprocessed result using the toggle or side-by-side view.
   - Note the detected deskew angle, CLAHE glare equalization, and bilateral filter noise reduction.
4. Click **"Extract & Verify Legal Metrology Compliance"**:
   - Review the calculated weighted score badge and status.
   - Hover over bounding boxes on the label to highlight the corresponding rule in the checklist.
   - Inspect violations to read the legal reference, plain-English explanation, and remediation advice.
5. Click **"Download PDF Audit"** to download the comprehensive ReportLab compliance PDF report.
6. Click **"Audit History"** in the top navigation to view historical verification runs recorded in SQLite.
7. Click **"Rules Guide"** to explore the reference guide for India's Legal Metrology Rules, 2011.
