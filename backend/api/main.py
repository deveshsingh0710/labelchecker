import os
import uuid
import json
import shutil
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request, Header, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from config import (
    BASE_DIR,
    DATA_DIR,
    UPLOAD_DIR,
    PREPROCESSED_DIR,
    REPORTS_DIR,
    SAMPLES_DIR,
    HOST,
    PORT,
    CORS_ORIGINS,
)
from database import (
    get_db,
    init_db,
    SessionLocal,
    Verification,
    Organization,
    User,
    DemoRequest,
    hash_password,
    DEMO_ORG_BRAND_ID,
    DEMO_ORG_GOVT_ID,
    DEMO_ORG_MARKETPLACE_ID,
)
from preprocessing import ImagePreprocessor
from ocr import TesseractOCREngine, LabelFieldParser
from compliance import ComplianceEngine
from reports import ComplianceReportGenerator

logger = logging.getLogger("labelcheck.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Shared global fallback instances
preprocessor = ImagePreprocessor()
ocr_engine = TesseractOCREngine()
compliance_engine = ComplianceEngine()
pdf_generator = ComplianceReportGenerator()


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    organization_name: str
    organization_type: str = "brand"  # brand | government | marketplace | audit_firm


class LoginRequest(BaseModel):
    email: str
    password: str


class DemoSubmission(BaseModel):
    name: str
    email: str
    organization_name: str
    organization_type: str  # brand | government | marketplace | audit_firm
    message: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler: moves heavy one-time initialization
    out of import time and provides startup timing metrics.
    """
    startup_start = time.perf_counter()
    logger.info("Starting LabelCheck API...")

    # 1. Database table initialization
    t0 = time.perf_counter()
    init_db()
    db_time = (time.perf_counter() - t0) * 1000
    logger.info(f"[Startup Stage 1/4] SQLite database verified in {db_time:.1f}ms")

    # 2. Image Preprocessor
    t0 = time.perf_counter()
    app.state.preprocessor = ImagePreprocessor()
    prep_time = (time.perf_counter() - t0) * 1000
    logger.info(f"[Startup Stage 2/4] OpenCV preprocessor ready in {prep_time:.1f}ms")

    # 3. Tesseract OCR Engine
    t0 = time.perf_counter()
    app.state.ocr_engine = TesseractOCREngine()
    ocr_init_time = (time.perf_counter() - t0) * 1000
    logger.info(f"[Startup Stage 3/4] Tesseract OCR engine initialized in {ocr_init_time:.1f}ms")

    # 4. Compliance Rule Engine & PDF Generator
    t0 = time.perf_counter()
    app.state.compliance_engine = ComplianceEngine()
    app.state.pdf_generator = ComplianceReportGenerator()
    rules_time = (time.perf_counter() - t0) * 1000
    logger.info(f"[Startup Stage 4/4] Compliance rules ({len(app.state.compliance_engine.ruleset.get('rules', []))} rules) & ReportLab ready in {rules_time:.1f}ms")

    total_startup_ms = (time.perf_counter() - startup_start) * 1000
    logger.info(f"LabelCheck backend startup successfully completed in {total_startup_ms:.1f}ms")

    yield

    logger.info("Shutting down LabelCheck API...")


app = FastAPI(
    title="LabelCheck API",
    description="Legal Metrology Packaged Commodity Compliance Verification API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend
is_wildcard = "*" in CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories for image access
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static/preprocessed", StaticFiles(directory=str(PREPROCESSED_DIR)), name="preprocessed")
app.mount("/static/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")


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
    sample_id: Optional[str] = Form(None),
    request: Request = None
):
    """
    Step 1 of verification: Uploads the label and applies the OpenCV pipeline.
    Returns the preprocessed image preview and transformation metrics.
    """
    t_start = time.perf_counter()
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

    active_preprocessor = getattr(request.app.state, "preprocessor", preprocessor) if request else preprocessor

    t_prep_start = time.perf_counter()
    try:
        prep_result = await run_in_threadpool(active_preprocessor.process, str(raw_path), str(prep_path))
    except Exception as e:
        logger.error(f"Image preprocessing failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Image preprocessing failed: {str(e)}")
    
    prep_time_ms = round((time.perf_counter() - t_prep_start) * 1000, 1)
    total_time_ms = round((time.perf_counter() - t_start) * 1000, 1)

    logger.info(
        f"[/api/preprocess] Completed for {original_filename} in {total_time_ms}ms "
        f"(OpenCV pipeline: {prep_time_ms}ms, deskew: {prep_result.deskew_angle}°)"
    )

    return {
        "file_id": file_id,
        "filename": original_filename,
        "raw_image_url": f"/static/uploads/{raw_path.name}",
        "preprocessed_image_url": f"/static/preprocessed/{prep_filename}",
        "binarized_image_url": f"/static/preprocessed/{Path(prep_result.binarized_path).name}",
        "deskew_angle": prep_result.deskew_angle,
        "original_dimensions": prep_result.original_dimensions,
        "preprocessed_dimensions": prep_result.preprocessed_dimensions,
        "metadata": prep_result.metadata,
        "timing_ms": {
            "pipeline_ms": prep_time_ms,
            "total_ms": total_time_ms,
            **prep_result.timing_ms
        }
    }


# In-memory tracking of background verification jobs
VERIFY_JOBS: Dict[str, Dict[str, Any]] = {}


def run_verification_pipeline(
    file_id: str,
    effective_org: str,
    raw_path_str: str,
    prep_path_str: str,
    filename: str,
) -> Dict[str, Any]:
    """
    Executes the full verification pipeline:
    1. Preprocessing (deskew, glare balancing, denoising, label region cropping)
    2. OCR extraction (Tesseract LSTM)
    3. Rule 6 statutory field parsing
    4. Compliance rule evaluation
    5. Database persistence
    Updates job status in VERIFY_JOBS dict for asynchronous polling clients.
    """
    t_verify_start = time.perf_counter()
    timing: Dict[str, float] = {}
    raw_path = Path(raw_path_str)
    prep_path = Path(prep_path_str)

    try:
        # Phase 1: Preprocessing if needed
        if file_id in VERIFY_JOBS:
            VERIFY_JOBS[file_id].update({
                "status": "PROCESSING",
                "progress": 25,
                "phase": "Isolating label region & OpenCV preprocessing",
                "updated_at": time.time(),
            })

        t0 = time.perf_counter()
        if not prep_path.exists():
            preprocessor.process(str(raw_path), str(prep_path))
        timing["image_prep_stage_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        binarized_path = PREPROCESSED_DIR / f"preprocessed_{file_id}_binarized.png"
        grayscale_path = PREPROCESSED_DIR / f"preprocessed_{file_id}_grayscale.png"

        # Phase 2: OCR extraction
        if file_id in VERIFY_JOBS:
            VERIFY_JOBS[file_id].update({
                "status": "PROCESSING",
                "progress": 60,
                "phase": "Extracting text with Tesseract OCR",
                "updated_at": time.time(),
            })

        t0 = time.perf_counter()
        ocr_result = ocr_engine.extract(
            str(prep_path),
            raw_image_path=str(raw_path),
            binarized_path=str(binarized_path) if binarized_path.exists() else None,
            grayscale_path=str(grayscale_path) if grayscale_path.exists() else None,
        )
        ocr_duration_ms = round((time.perf_counter() - t0) * 1000, 1)
        timing["ocr_stage_ms"] = ocr_duration_ms

        if ocr_duration_ms > 10000:
            logger.warning(
                f"[PERFORMANCE WARNING] [/api/verify] OCR stage for '{filename}' ({file_id}) took "
                f"{ocr_duration_ms / 1000.0:.2f}s (> 10.0s)!"
            )

        raw_url = f"/static/uploads/{raw_path.name}"
        prep_url = f"/static/preprocessed/{prep_path.name}"

        # Item 4: Distinct error handling for timeout vs crash vs genuine empty text
        if ocr_result.timed_out:
            logger.warning(f"Verification aborted for {file_id}: OCR processing timed out.")
            res_payload = {
                "id": file_id,
                "organization_id": effective_org,
                "filename": filename,
                "raw_image_url": raw_url,
                "preprocessed_image_url": prep_url,
                "ocr_summary": ocr_result.to_dict(),
                "overall_score": 0.0,
                "compliance_status": "NON_COMPLIANT",
                "total_passed": 0,
                "total_failed": 0,
                "total_needs_review": 0,
                "extracted_fields": {},
                "evaluation_results": [],
                "error_message": "Processing took too long, please try a smaller or clearer image.",
                "quality_warning": "Processing took too long, please try a smaller or clearer image.",
                "pdf_report_url": None,
                "timing_ms": timing,
                "error_type": "TIMEOUT",
            }
            if file_id in VERIFY_JOBS:
                VERIFY_JOBS[file_id].update({
                    "status": "FAILED",
                    "progress": 100,
                    "phase": "Timeout",
                    "error": "Processing took too long, please try a smaller or clearer image.",
                    "result": res_payload,
                    "updated_at": time.time(),
                })
            return res_payload

        if ocr_result.error_message and not ocr_result.raw_text.strip():
            logger.error(f"Verification aborted for {file_id}: {ocr_result.error_message}")
            res_payload = {
                "id": file_id,
                "organization_id": effective_org,
                "filename": filename,
                "raw_image_url": raw_url,
                "preprocessed_image_url": prep_url,
                "ocr_summary": ocr_result.to_dict(),
                "overall_score": 0.0,
                "compliance_status": "NON_COMPLIANT",
                "total_passed": 0,
                "total_failed": 0,
                "total_needs_review": 0,
                "extracted_fields": {},
                "evaluation_results": [],
                "error_message": ocr_result.error_message,
                "quality_warning": ocr_result.quality_message,
                "pdf_report_url": None,
                "timing_ms": timing,
                "error_type": "ERROR",
            }
            if file_id in VERIFY_JOBS:
                VERIFY_JOBS[file_id].update({
                    "status": "FAILED",
                    "progress": 100,
                    "phase": "Error",
                    "error": ocr_result.error_message,
                    "result": res_payload,
                    "updated_at": time.time(),
                })
            return res_payload

        if not ocr_result.raw_text.strip():
            # Genuine empty OCR result (blank/obstructed label)
            res_payload = {
                "id": file_id,
                "organization_id": effective_org,
                "filename": filename,
                "raw_image_url": raw_url,
                "preprocessed_image_url": prep_url,
                "ocr_summary": {
                    "raw_text": "",
                    "average_confidence": 0.0,
                    "total_words": 0,
                    "total_lines": 0,
                    "low_quality_warning": True,
                    "quality_message": "Low image quality — please retake photo with better lighting and focus.",
                },
                "overall_score": 0.0,
                "compliance_status": "NON_COMPLIANT",
                "total_passed": 0,
                "total_failed": 0,
                "total_needs_review": 0,
                "extracted_fields": {},
                "evaluation_results": [],
                "error_message": "No readable text detected. Please ensure the label is sharp, well-lit, and not obstructed.",
                "quality_warning": "Low image quality — please retake photo with better lighting and focus.",
                "pdf_report_url": None,
                "timing_ms": timing,
                "error_type": "EMPTY_TEXT",
            }
            if file_id in VERIFY_JOBS:
                VERIFY_JOBS[file_id].update({
                    "status": "COMPLETED",
                    "progress": 100,
                    "phase": "Completed",
                    "result": res_payload,
                    "updated_at": time.time(),
                })
            return res_payload

        # Phase 3: Field parsing
        if file_id in VERIFY_JOBS:
            VERIFY_JOBS[file_id].update({
                "status": "PROCESSING",
                "progress": 80,
                "phase": "Parsing Legal Metrology statutory fields",
                "updated_at": time.time(),
            })

        t0 = time.perf_counter()
        parser = LabelFieldParser(ocr_result)
        extracted_fields_dict = parser.extract_all()
        timing["parsing_stage_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # Phase 4: Compliance evaluation
        if file_id in VERIFY_JOBS:
            VERIFY_JOBS[file_id].update({
                "status": "PROCESSING",
                "progress": 90,
                "phase": "Evaluating Rule 6 statutory compliance",
                "updated_at": time.time(),
            })

        t0 = time.perf_counter()
        compliance_summary = compliance_engine.evaluate(
            extracted_fields_dict,
            overall_ocr_confidence=ocr_result.average_confidence,
        )
        timing["compliance_eval_stage_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        serializable_fields = {k: v.to_dict() for k, v in extracted_fields_dict.items()}
        serializable_eval = [item.to_dict() for item in compliance_summary.items]

        # Phase 5: Persist to DB
        t0 = time.perf_counter()
        db = SessionLocal()
        try:
            verification_record = Verification(
                id=file_id,
                organization_id=effective_org,
                filename=filename,
                original_image=raw_url,
                preprocessed_image=prep_url,
                overall_score=compliance_summary.overall_score,
                compliance_status=compliance_summary.compliance_status,
                total_passed=compliance_summary.total_passed,
                total_failed=compliance_summary.total_failed,
                total_needs_review=compliance_summary.total_needs_review,
                extracted_fields=json.dumps(serializable_fields),
                evaluation_results=json.dumps(serializable_eval),
            )
            db.merge(verification_record)
            db.commit()
        finally:
            db.close()

        timing["db_commit_stage_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        total_verify_ms = round((time.perf_counter() - t_verify_start) * 1000, 1)
        timing["total_verify_ms"] = total_verify_ms

        res_payload = {
            "id": file_id,
            "organization_id": effective_org,
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
            "quality_warning": ocr_result.quality_message if ocr_result.low_quality_warning else None,
            "pdf_report_url": f"/api/verifications/{file_id}/pdf",
            "timing_ms": timing,
        }

        if file_id in VERIFY_JOBS:
            VERIFY_JOBS[file_id].update({
                "status": "COMPLETED",
                "progress": 100,
                "phase": "Completed",
                "result": res_payload,
                "updated_at": time.time(),
            })

        logger.info(
            f"Verification completed for {filename} ({file_id}) in {total_verify_ms}ms: "
            f"Score={compliance_summary.overall_score:.1f}, Conf={ocr_result.average_confidence:.1f}%"
        )
        return res_payload

    except Exception as e:
        logger.error(f"Verification pipeline failed for {file_id}: {e}", exc_info=True)
        if file_id in VERIFY_JOBS:
            VERIFY_JOBS[file_id].update({
                "status": "FAILED",
                "error": str(e),
                "phase": "Error",
                "updated_at": time.time(),
            })
        raise


@app.post("/api/verify")
async def verify_label(
    file_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None),
    organization_id: Optional[str] = Form(None),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    sync: bool = Query(False),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Step 2: Runs OCR extraction and rule engine compliance evaluation.
    Default async mode: enqueues background processing task and returns HTTP 202 Accepted.
    Client polls GET /api/verify/status/{file_id} until completed.
    Sync mode (?sync=true): executes synchronously and returns full result with HTTP 200.
    """
    active_preprocessor = getattr(request.app.state, "preprocessor", preprocessor) if request else preprocessor

    # 1. Determine raw and preprocessed images
    if file_id and isinstance(file_id, str) and file_id.strip():
        matched_raw = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        if not matched_raw:
            raise HTTPException(status_code=404, detail="Uploaded file session not found")
        raw_path = matched_raw[0]
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"
        if not prep_path.exists():
            active_preprocessor.process(str(raw_path), str(prep_path))
        filename = raw_path.name
    elif sample_id and isinstance(sample_id, str) and sample_id.strip():
        prep_resp = await preprocess_image(file=None, sample_id=sample_id, request=request)
        file_id = prep_resp["file_id"]
        matched_raw = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        raw_path = matched_raw[0]
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"
        filename = f"{sample_id}.png"
    elif file is not None and hasattr(file, "filename") and file.filename:
        prep_resp = await preprocess_image(file=file, sample_id=None, request=request)
        file_id = prep_resp["file_id"]
        matched_raw = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        raw_path = matched_raw[0]
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"
        filename = file.filename or "upload.jpg"
    else:
        raise HTTPException(status_code=400, detail="Must provide file_id, file, or sample_id")

    effective_org = organization_id or x_organization_id or DEMO_ORG_BRAND_ID

    # Synchronous execution mode (for testing or clients requiring blocking response)
    if sync or background_tasks is None:
        result = await run_in_threadpool(
            run_verification_pipeline,
            file_id,
            effective_org,
            str(raw_path),
            str(prep_path),
            filename,
        )
        return result

    # Asynchronous execution mode: initialize job and spawn background task
    VERIFY_JOBS[file_id] = {
        "status": "PROCESSING",
        "progress": 20,
        "phase": "Isolating label region & preprocessing",
        "result": None,
        "error": None,
        "updated_at": time.time(),
    }
    background_tasks.add_task(
        run_verification_pipeline,
        file_id,
        effective_org,
        str(raw_path),
        str(prep_path),
        filename,
    )

    return JSONResponse(
        status_code=202,
        content={
            "status": "PROCESSING",
            "file_id": file_id,
            "progress": 20,
            "phase": "Isolating label region & preprocessing",
            "message": "Verification analysis started in background",
        },
    )


@app.get("/api/verify/status/{file_id}")
def get_verification_status(
    file_id: str,
    db: Session = Depends(get_db),
):
    """
    Polls the verification job progress for an asynchronous verification.
    Returns status: PROCESSING | COMPLETED | FAILED along with progress % and result.
    """
    if file_id in VERIFY_JOBS:
        job = VERIFY_JOBS[file_id]
        return {
            "status": job["status"],
            "progress": job.get("progress", 0),
            "phase": job.get("phase", ""),
            "result": job.get("result"),
            "error": job.get("error"),
            "file_id": file_id,
        }

    # Fallback to database if completed earlier or job dict cleared
    record = db.query(Verification).filter(Verification.id == file_id).first()
    if record:
        return {
            "status": "COMPLETED",
            "progress": 100,
            "phase": "Completed",
            "result": record.to_dict(),
            "error": None,
            "file_id": file_id,
        }

    raise HTTPException(status_code=404, detail=f"Verification job '{file_id}' not found")


@app.get("/api/verifications")
def list_verifications(
    organization_id: Optional[str] = None,
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Returns historical label verification audits, optionally scoped to an organization."""
    effective_org = organization_id or x_organization_id
    query = db.query(Verification)
    if effective_org and effective_org.strip() and effective_org != "all":
        query = query.filter(Verification.organization_id == effective_org.strip())
    records = query.order_by(Verification.created_at.desc()).limit(limit).all()
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
def download_pdf_report(v_id: str, db: Session = Depends(get_db), request: Request = None):
    """
    Generates on-the-fly or returns existing PDF report for the verification.
    Guaranteed on-demand execution with latency logging.
    """
    t0 = time.perf_counter()
    record = db.query(Verification).filter(Verification.id == v_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Verification record not found")

    pdf_filename = f"LabelCheck_Report_{v_id}.pdf"
    pdf_path = REPORTS_DIR / pdf_filename

    # If not already generated, generate now
    if not pdf_path.exists():
        prep_path = PREPROCESSED_DIR / f"preprocessed_{v_id}.jpg"
        if not prep_path.exists():
            matched = list(UPLOAD_DIR.glob(f"{v_id}.*"))
            img_source = str(matched[0]) if matched else None
        else:
            img_source = str(prep_path)

        if not img_source or not os.path.exists(img_source):
            raise HTTPException(status_code=404, detail="Source image not found to build report")

        active_pdf_gen = getattr(request.app.state, "pdf_generator", pdf_generator) if request else pdf_generator
        active_pdf_gen.generate(record.to_dict(), img_source, output_filename=pdf_filename)
        elapsed_pdf = round((time.perf_counter() - t0) * 1000, 1)
        logger.info(f"[/api/verifications/{v_id}/pdf] Generated ReportLab PDF in {elapsed_pdf}ms")
    else:
        logger.info(f"[/api/verifications/{v_id}/pdf] Returning existing cached PDF for {v_id}")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_filename,
        headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
    )


@app.get("/api/analytics")
def get_analytics(
    organization_id: Optional[str] = None,
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    db: Session = Depends(get_db)
):
    """Calculates aggregated compliance rates, score averages, and violation frequencies."""
    effective_org = organization_id or x_organization_id
    query = db.query(Verification)
    if effective_org and effective_org.strip() and effective_org != "all":
        query = query.filter(Verification.organization_id == effective_org.strip())
    records = query.all()

    total_scans = len(records)
    if total_scans == 0:
        return {
            "total_scans": 0,
            "compliant_count": 0,
            "partially_compliant_count": 0,
            "non_compliant_count": 0,
            "compliance_rate": 0.0,
            "average_score": 0.0,
            "top_violations": [],
            "status_breakdown": [
                {"name": "Compliant", "value": 0, "color": "#10B981"},
                {"name": "Partially Compliant", "value": 0, "color": "#F59E0B"},
                {"name": "Non-Compliant", "value": 0, "color": "#F43F5E"},
            ]
        }

    comp_count = sum(1 for r in records if r.compliance_status == "COMPLIANT")
    part_count = sum(1 for r in records if r.compliance_status == "PARTIALLY_COMPLIANT")
    non_comp_count = sum(1 for r in records if r.compliance_status == "NON_COMPLIANT")
    avg_score = round(sum(r.overall_score for r in records) / total_scans, 1)
    comp_rate = round((comp_count / total_scans) * 100.0, 1)

    # Aggregate violations across all scans
    violation_counts: Dict[str, Dict[str, Any]] = {}
    for r in records:
        try:
            eval_items = json.loads(r.evaluation_results) if r.evaluation_results else []
            for ev in eval_items:
                if ev.get("status") in ("FAIL", "NEEDS_REVIEW"):
                    rule_id = ev.get("rule_id", "unknown_rule")
                    rule_name = ev.get("rule_name", rule_id.replace("_", " ").title())
                    legal_ref = ev.get("legal_reference", "Legal Metrology 2011")
                    if rule_id not in violation_counts:
                        violation_counts[rule_id] = {
                            "rule_id": rule_id,
                            "rule_name": rule_name,
                            "legal_reference": legal_ref,
                            "count": 0,
                        }
                    violation_counts[rule_id]["count"] += 1
        except Exception:
            continue

    sorted_violations = sorted(
        violation_counts.values(),
        key=lambda x: x["count"],
        reverse=True
    )[:8]

    for v in sorted_violations:
        v["percentage"] = round((v["count"] / total_scans) * 100.0, 1)

    return {
        "total_scans": total_scans,
        "compliant_count": comp_count,
        "partially_compliant_count": part_count,
        "non_compliant_count": non_comp_count,
        "compliance_rate": comp_rate,
        "average_score": avg_score,
        "top_violations": sorted_violations,
        "status_breakdown": [
            {"name": "Compliant", "value": comp_count, "color": "#10B981"},
            {"name": "Partially Compliant", "value": part_count, "color": "#F59E0B"},
            {"name": "Non-Compliant", "value": non_comp_count, "color": "#F43F5E"},
        ]
    }


@app.get("/api/organizations/demo")
def get_demo_organizations(db: Session = Depends(get_db)):
    """Returns seeded demo organizations for quick 1-click tenant switching in hackathon demo."""
    orgs = db.query(Organization).all()
    out = []
    for org in orgs:
        d = org.to_dict()
        user = db.query(User).filter(User.organization_id == org.id).first()
        d["default_user"] = user.to_dict() if user else None
        out.append(d)
    return {"organizations": out}


@app.post("/api/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    """Registers a new user and organization."""
    existing = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_org = Organization(
        id=str(uuid.uuid4()),
        name=req.organization_name.strip(),
        type=req.organization_type.strip().lower()
    )
    db.add(new_org)
    db.flush()

    new_user = User(
        id=str(uuid.uuid4()),
        email=req.email.strip().lower(),
        password_hash=hash_password(req.password),
        name=req.name.strip(),
        organization_id=new_org.id,
        role="admin"
    )
    db.add(new_user)
    db.commit()

    return {
        "status": "success",
        "token": f"token-{new_user.id}",
        "user": new_user.to_dict(),
        "organization": new_org.to_dict()
    }


@app.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates credentials and returns user and organization profile."""
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or user.password_hash != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    return {
        "status": "success",
        "token": f"token-{user.id}",
        "user": user.to_dict(),
        "organization": org.to_dict() if org else None
    }


@app.get("/api/auth/me")
def get_current_user(
    authorization: Optional[str] = Header(None),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    db: Session = Depends(get_db)
):
    """Returns current active user / organization context."""
    if authorization and "token-" in authorization:
        user_id = authorization.replace("Bearer ", "").replace("token-", "").strip()
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            return {"user": user.to_dict(), "organization": org.to_dict() if org else None}

    # Fallback to demo org
    org_id = x_organization_id or DEMO_ORG_BRAND_ID
    org = db.query(Organization).filter(Organization.id == org_id).first()
    user = db.query(User).filter(User.organization_id == org_id).first() if org else None
    return {
        "user": user.to_dict() if user else None,
        "organization": org.to_dict() if org else None
    }


@app.post("/api/demo-request")
def submit_demo_request(req: DemoSubmission, db: Session = Depends(get_db)):
    """Stores inbound enterprise/government demo requests in database."""
    if not req.name.strip() or not req.email.strip() or not req.organization_name.strip():
        raise HTTPException(status_code=400, detail="Name, email, and organization name are required")

    demo = DemoRequest(
        id=str(uuid.uuid4()),
        name=req.name.strip(),
        email=req.email.strip().lower(),
        organization_name=req.organization_name.strip(),
        organization_type=req.organization_type.strip(),
        message=req.message.strip() if req.message else None,
        status="pending"
    )
    db.add(demo)
    db.commit()

    return {
        "status": "success",
        "request_id": demo.id,
        "message": "Thank you! Your demo request has been received. Our compliance advisory team will reach out within 24 hours."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
