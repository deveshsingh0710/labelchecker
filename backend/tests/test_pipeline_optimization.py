import os
import unittest
import numpy as np
import cv2
from pathlib import Path

from preprocessing.pipeline import ImagePreprocessor
from ocr.tesseract_engine import TesseractOCREngine
from api.main import VERIFY_JOBS, run_verification_pipeline, SAMPLES_DIR, UPLOAD_DIR, PREPROCESSED_DIR
from database import SessionLocal, Verification, DEMO_ORG_BRAND_ID


class TestPipelineOptimization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preprocessor = ImagePreprocessor()
        cls.ocr_engine = TesseractOCREngine()

    def test_label_region_clutter_cropping(self):
        """Synthesizes a label on a large background clutter and verifies it gets cropped."""
        # Create 1000x1000 image with dark desk background
        img = np.zeros((1000, 1000, 3), dtype=np.uint8)
        img[:] = (30, 30, 30)

        # Place a bright, text-dense rectangular label in the center (x: 250..750, y: 200..800) -> 50% of image area
        cv2.rectangle(img, (250, 200), (750, 800), (245, 245, 245), -1)
        for y in range(250, 750, 40):
            cv2.putText(
                img,
                "LEGAL METROLOGY MRP RS 199 NET 100g",
                (270, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (10, 10, 10),
                2,
            )

        cropped, crop_box, is_cropped = self.preprocessor.detect_label_region(img)
        self.assertTrue(is_cropped, "Expected label region to be detected and cropped")
        self.assertIsNotNone(crop_box)
        x, y, w, h = crop_box
        # Verify crop box closely matches the label region (with safety padding)
        self.assertLessEqual(x, 260)
        self.assertGreaterEqual(x + w, 740)
        self.assertLessEqual(y, 210)
        self.assertGreaterEqual(y + h, 790)

    def test_label_region_clean_fallback(self):
        """Verifies that clean, full-frame labels are NOT cropped and fallback gracefully."""
        # Create full-frame white label with text everywhere
        img = np.ones((600, 800, 3), dtype=np.uint8) * 255
        for y in range(40, 580, 50):
            cv2.putText(
                img,
                "FULL FRAME COMMODITY LABEL SPECIFICATIONS",
                (30, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 0),
                2,
            )

        cropped, crop_box, is_cropped = self.preprocessor.detect_label_region(img)
        self.assertFalse(is_cropped, "Full frame label should not trigger cropping")
        self.assertIsNone(crop_box)
        self.assertEqual(cropped.shape, img.shape)

    def test_ocr_fast_early_exit_on_noise(self):
        """Verifies that completely blank or noisy images trigger fast early exit."""
        blank_path = Path("data/uploads/test_blank.png")
        blank_path.parent.mkdir(parents=True, exist_ok=True)
        blank = np.zeros((400, 400), dtype=np.uint8)
        cv2.imwrite(str(blank_path), blank)

        try:
            res = self.ocr_engine.extract(str(blank_path))
            self.assertTrue(res.low_quality_warning)
            self.assertEqual(len(res.words), 0)
        finally:
            if blank_path.exists():
                blank_path.unlink()

    def test_async_verification_pipeline_execution(self):
        """Tests run_verification_pipeline executes end-to-end, records job progress and saves DB."""
        file_id = "test_opt_sample"
        sample_path = SAMPLES_DIR / "sample_compliant.png"
        raw_path = UPLOAD_DIR / f"{file_id}.png"
        prep_path = PREPROCESSED_DIR / f"preprocessed_{file_id}.jpg"

        import shutil
        shutil.copyfile(str(sample_path), str(raw_path))

        # Register in VERIFY_JOBS
        VERIFY_JOBS[file_id] = {
            "status": "PROCESSING",
            "progress": 20,
            "phase": "Starting",
            "result": None,
            "error": None,
        }

        result = run_verification_pipeline(
            file_id=file_id,
            effective_org=DEMO_ORG_BRAND_ID,
            raw_path_str=str(raw_path),
            prep_path_str=str(prep_path),
            filename="sample_compliant.png",
        )

        # Check job completion state in VERIFY_JOBS
        self.assertEqual(VERIFY_JOBS[file_id]["status"], "COMPLETED")
        self.assertEqual(VERIFY_JOBS[file_id]["progress"], 100)
        self.assertIsNotNone(VERIFY_JOBS[file_id]["result"])

        # Check result payload structure
        self.assertEqual(result["id"], file_id)
        self.assertIn(result["compliance_status"], ["COMPLIANT", "PARTIALLY_COMPLIANT"])
        self.assertGreaterEqual(result["overall_score"], 70.0)

        # Check DB record
        db = SessionLocal()
        try:
            record = db.query(Verification).filter(Verification.id == file_id).first()
            self.assertIsNotNone(record)
            self.assertEqual(record.filename, "sample_compliant.png")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
