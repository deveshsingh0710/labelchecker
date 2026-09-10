import os
import uuid
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from config import (
    BASE_DIR,
    DATA_DIR,
    UPLOAD_DIR,
    PREPROCESSED_DIR,
    REPORTS_DIR,
    SAMPLES_DIR,
)
from database import get_db, init_db, Verification
from preprocessing import ImagePreprocessor
from ocr import TesseractOCREngine, LabelFieldParser
from compliance import ComplianceEngine
from reports import ComplianceReportGenerator

# Initialize database tables
init_db()

app = FastAPI(
    title="LabelCheck API",
    description="Legal Metrology Packaged Commodity Compliance Verification API",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories for image access
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static/preprocessed", StaticFiles(directory=str(PREPROCESSED_DIR)), name="preprocessed")
app.mount("/static/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")

# Reusable instances
preprocessor = ImagePreprocessor()
ocr_engine = TesseractOCREngine()
compliance_engine = ComplianceEngine()
pdf_generator = ComplianceReportGenerator()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "LabelCheck API",
        "version": "1.0.0"
    }


@app.get("/api/samples")
def get_sample_labels():
    """Returns preset packaged commodity label samples for instant testing."""
    samples = [
        {
            "id": "sample_compliant",
            "title": "Fully Compliant Snack Label",
            "description": "Roasted Almonds label complying with all mandatory declarations under Rule 6(1).",
            "filename": "sample_compliant.png",
            "image_url": "/static/samples/sample_compliant.png",
            "expected_status": "COMPLIANT"
        },
        {
            "id": "sample_violations",
            "title": "Non-Compliant Cookies Label",
            "description": "Packaged cookies with missing customer care, non-standard unit 'gms', and missing tax clause.",
            "filename": "sample_violations.png",
            "image_url": "/static/samples/sample_violations.png",
            "expected_status": "NON_COMPLIANT"
        },
        {
            "id": "sample_imported",
            "title": "Imported Dark Chocolate Label",
            "description": "Imported chocolate package verifying country of origin and importer details under Rule 6(1)(n).",
            "filename": "sample_imported.png",
            "image_url": "/static/samples/sample_imported.png",
            "expected_status": "PARTIALLY_COMPLIANT"
        }
    ]
    return {"samples": samples}


@app.post("/api/preprocess")
async def preprocess_image(
    file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None)
):
    """
    Step 1 of verification: Uploads the label and applies the OpenCV pipeline.
    Returns the preprocessed image preview and transformation metrics.
    """
    file_id = str(uuid.uuid4())
    original_filename = "label.png"

    if sample_id:
        sample_path = SAMPLES_DIR / f"{sample_id}.png"
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")
        ext = ".png"
        raw_path = UPLOAD_DIR / f"{file_id}{ext}"
        shutil.copyfile(str(sample_path), str(raw_path))
        original_filename = f"{sample_id}.png"
    elif file:
        original_filename = file.filename or "upload.jpg"
        ext = Path(original_filename).suffix.lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"):
            raise HTTPException(status_code=400, detail="Supported image formats: JPG, PNG, WebP, BMP, HEIC")
        raw_path = UPLOAD_DIR / f"{file_id}{ext}"
        with open(raw_path, "wb") as f:
            content = await file.read()
            f.write(content)
    else:
        raise HTTPException(status_code=400, detail="Must provide an uploaded file or sample_id")

    # Run OpenCV Preprocessing Pipeline
    prep_filename = f"preprocessed_{file_id}.jpg"
    prep_path = PREPROCESSED_DIR / prep_filename

    try:
        prep_result = preprocessor.process(str(raw_path), str(prep_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image preprocessing failed: {str(e)}")

    return {
        "file_id": file_id,
        "filename": original_filename,
        "raw_image_url": f"/static/uploads/{raw_path.name}",
        "preprocessed_image_url": f"/static/preprocessed/{prep_filename}",
        "deskew_angle": prep_result.deskew_angle,
        "original_dimensions": prep_result.original_dimensions,
        "preprocessed_dimensions": prep_result.preprocessed_dimensions,
        "metadata": prep_result.metadata
    }


@app.post("/api/verify")
async def verify_label(
    file_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Step 2: Runs OCR extraction and rule engine compliance evaluation.
    Persists result in SQLite database and prepares PDF report generation.
    """
    # 1. Determine raw and preprocessed images
    if file_id and isinstance(file_id, str) and file_id.strip():
        # Match existing uploaded & preprocessed files
        matched_raw = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        if not matched_raw:
            raise HTTPException(status_code=404, detail="Uploaded file session not found")
        raw_path = matched_raw[0]
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"
        if not prep_path.exists():
            preprocessor.process(str(raw_path), str(prep_path))
        filename = raw_path.name
    elif sample_id and isinstance(sample_id, str) and sample_id.strip():
        prep_resp = await preprocess_image(file=None, sample_id=sample_id)
        file_id = prep_resp["file_id"]
        matched_raw = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        raw_path = matched_raw[0]
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"
        filename = f"{sample_id}.png"
    elif file is not None and hasattr(file, "filename") and file.filename:
        prep_resp = await preprocess_image(file=file, sample_id=None)
        file_id = prep_resp["file_id"]
        matched_raw = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        raw_path = matched_raw[0]
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"
        filename = file.filename or "upload.jpg"
    else:
        raise HTTPException(status_code=400, detail="Must provide file_id, file, or sample_id")

    # 2. Run OCR extraction (multi-pass combining preprocessed and raw image)
    try:
        ocr_result = ocr_engine.extract(str(prep_path), raw_image_path=str(raw_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")

    if not ocr_result.raw_text.strip():
        # Handle blurry / no text image gracefully
        return JSONResponse(
            status_code=200,
            content={
                "id": file_id,
                "filename": filename,
                "raw_image_url": f"/static/uploads/{raw_path.name}",
                "preprocessed_image_url": f"/static/preprocessed/{prep_path.name}",
                "ocr_summary": {
                    "raw_text": "",
                    "average_confidence": 0.0,
                    "total_words": 0,
                    "total_lines": 0
                },
                "overall_score": 0.0,
                "compliance_status": "NON_COMPLIANT",
                "total_passed": 0,
                "total_failed": 0,
                "total_needs_review": 0,
                "extracted_fields": {},
                "evaluation_results": [],
                "error_message": "No readable text detected. Please ensure the label is sharp, well-lit, and not obstructed.",
                "pdf_report_url": None
            }
        )

    # 3. Parse fields
    parser = LabelFieldParser(ocr_result)
    extracted_fields_dict = parser.extract_all()

    # 4. Evaluate compliance rules
    compliance_summary = compliance_engine.evaluate(
        extracted_fields_dict,
        overall_ocr_confidence=ocr_result.average_confidence
    )

    # Serialize extracted fields and evaluation results
    serializable_fields = {k: v.to_dict() for k, v in extracted_fields_dict.items()}
    serializable_eval = [item.to_dict() for item in compliance_summary.items]

    raw_url = f"/static/uploads/{raw_path.name}"
    prep_url = f"/static/preprocessed/{prep_path.name}"

    # 5. Persist into database
    verification_record = Verification(
        id=file_id,
        filename=filename,
        original_image=raw_url,
        preprocessed_image=prep_url,
        overall_score=compliance_summary.overall_score,
        compliance_status=compliance_summary.compliance_status,
        total_passed=compliance_summary.total_passed,
        total_failed=compliance_summary.total_failed,
        total_needs_review=compliance_summary.total_needs_review,
        extracted_fields=json.dumps(serializable_fields),
        evaluation_results=json.dumps(serializable_eval)
    )

    db.merge(verification_record)
    db.commit()

    return {
        "id": file_id,
        "filename": filename,
        "raw_image_url": raw_url,
        "preprocessed_image_url": prep_url,
        "ocr_summary": ocr_result.to_dict(),
        "overall_score": round(compliance_summary.overall_score, 1),
        "compliance_status": compliance_summary.compliance_status,
        "total_passed": compliance_summary.total_passed,
        "total_failed": compliance_summary.total_failed,
        "total_needs_review": compliance_summary.total_needs_review,
        "extracted_fields": serializable_fields,
        "evaluation_results": serializable_eval,
        "pdf_report_url": f"/api/verifications/{file_id}/pdf"
    }


@app.get("/api/verifications")
def list_verifications(limit: int = 20, db: Session = Depends(get_db)):
    """Returns historical label verification audits."""
    records = db.query(Verification).order_by(Verification.created_at.desc()).limit(limit).all()
    return {"verifications": [r.to_dict() for r in records]}


@app.get("/api/verifications/{v_id}")
def get_verification(v_id: str, db: Session = Depends(get_db)):
    """Returns single verification detail."""
    record = db.query(Verification).filter(Verification.id == v_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Verification record not found")
    data = record.to_dict()
    data["pdf_report_url"] = f"/api/verifications/{v_id}/pdf"
    return data


@app.get("/api/verifications/{v_id}/pdf")
def download_pdf_report(v_id: str, db: Session = Depends(get_db)):
    """Generates on-the-fly or returns existing PDF report for the verification."""
    record = db.query(Verification).filter(Verification.id == v_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Verification record not found")

    pdf_filename = f"LabelCheck_Report_{v_id}.pdf"
    pdf_path = REPORTS_DIR / pdf_filename

    # If not already generated, generate now
    if not pdf_path.exists():
        # Find preprocessed or raw image
        prep_path = PREPROCESSED_DIR / f"preprocessed_{v_id}.jpg"
        if not prep_path.exists():
            matched = list(UPLOAD_DIR.glob(f"{v_id}.*"))
            img_source = str(matched[0]) if matched else None
        else:
            img_source = str(prep_path)

        if not img_source or not os.path.exists(img_source):
            raise HTTPException(status_code=404, detail="Source image not found to build report")

        pdf_generator.generate(record.to_dict(), img_source, output_filename=pdf_filename)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_filename,
        headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
