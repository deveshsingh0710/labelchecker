import os
import unittest
from pathlib import Path

from preprocessing import ImagePreprocessor
from ocr import TesseractOCREngine, LabelFieldParser
from compliance import ComplianceEngine

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "preprocessed" / "tests"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TestOCRFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preprocessor = ImagePreprocessor()
        cls.ocr_engine = TesseractOCREngine()
        cls.compliance_engine = ComplianceEngine()

    def test_fixture_sharp_high_accuracy(self):
        """Validates that clean sharp labels achieve high confidence and 100% field extraction."""
        img_path = FIXTURES_DIR / "fixture_sharp.png"
        self.assertTrue(img_path.exists(), f"Fixture missing at {img_path}")

        out_prep = OUTPUT_DIR / "test_sharp.jpg"
        prep_res = self.preprocessor.process(str(img_path), str(out_prep))

        # Check binarized file was generated and saved
        self.assertTrue(os.path.exists(prep_res.binarized_path))
        self.assertTrue(os.path.exists(prep_res.grayscale_path))

        ocr_res = self.ocr_engine.extract(
            str(out_prep),
            binarized_path=prep_res.binarized_path,
            grayscale_path=prep_res.grayscale_path
        )

        # Assert confidence is significantly high (> 75%)
        self.assertGreaterEqual(ocr_res.average_confidence, 75.0)

        parser = LabelFieldParser(ocr_res)
        fields = parser.extract_all()

        # Check mandatory fields
        self.assertTrue(fields["net_quantity"].found, "Net quantity not found")
        self.assertEqual(fields["net_quantity"].value, "500 g")
        self.assertTrue(fields["net_quantity"].details.get("is_standard_unit"))

        self.assertTrue(fields["mrp"].found, "MRP not found")
        self.assertIn("299", fields["mrp"].value)
        self.assertTrue(fields["mrp"].details.get("has_tax_clause"))

        self.assertTrue(fields["manufacture_date"].found, "Mfg date not found")
        self.assertEqual(fields["manufacture_date"].value, "09/2026")

        self.assertTrue(fields["customer_care_details"].found, "Customer care not found")
        self.assertIn("1800", fields["customer_care_details"].value)

        # Full compliance check
        summary = self.compliance_engine.evaluate(fields, overall_ocr_confidence=ocr_res.average_confidence)
        self.assertEqual(summary.compliance_status, "COMPLIANT")
        self.assertGreaterEqual(summary.overall_score, 85.0)

    def test_fixture_angled_auto_deskew(self):
        """Validates that a 3-degree rotated image is detected and corrected by auto_deskew."""
        img_path = FIXTURES_DIR / "fixture_angled.png"
        self.assertTrue(img_path.exists(), f"Fixture missing at {img_path}")

        out_prep = OUTPUT_DIR / "test_angled.jpg"
        prep_res = self.preprocessor.process(str(img_path), str(out_prep))

        # Deskew angle should be detected in the range of 1.5° to 4.5°
        self.assertGreaterEqual(abs(prep_res.deskew_angle), 1.0)
        self.assertLessEqual(abs(prep_res.deskew_angle), 5.0)

        # OCR should still successfully extract fields after deskewing
        ocr_res = self.ocr_engine.extract(
            str(out_prep),
            binarized_path=prep_res.binarized_path,
            grayscale_path=prep_res.grayscale_path
        )
        self.assertGreaterEqual(ocr_res.average_confidence, 65.0)

        parser = LabelFieldParser(ocr_res)
        fields = parser.extract_all()
        self.assertTrue(fields["net_quantity"].found)
        self.assertTrue(fields["mrp"].found)

    def test_fixture_low_light_enhancement(self):
        """Validates that low-light / underexposed images are restored via CLAHE and binarized."""
        img_path = FIXTURES_DIR / "fixture_low_light.png"
        self.assertTrue(img_path.exists(), f"Fixture missing at {img_path}")

        out_prep = OUTPUT_DIR / "test_low_light.jpg"
        prep_res = self.preprocessor.process(str(img_path), str(out_prep))

        ocr_res = self.ocr_engine.extract(
            str(out_prep),
            binarized_path=prep_res.binarized_path,
            grayscale_path=prep_res.grayscale_path
        )
        self.assertGreaterEqual(ocr_res.average_confidence, 65.0)

        parser = LabelFieldParser(ocr_res)
        fields = parser.extract_all()
        self.assertTrue(fields["net_quantity"].found or fields["mrp"].found)

    def test_fixture_glossy_glare_handling(self):
        """Validates that glossy specular glare is mitigated via median denoising & thresholding."""
        img_path = FIXTURES_DIR / "fixture_glossy_glare.png"
        self.assertTrue(img_path.exists(), f"Fixture missing at {img_path}")

        out_prep = OUTPUT_DIR / "test_glare.jpg"
        prep_res = self.preprocessor.process(str(img_path), str(out_prep))

        ocr_res = self.ocr_engine.extract(
            str(out_prep),
            binarized_path=prep_res.binarized_path,
            grayscale_path=prep_res.grayscale_path
        )
        self.assertGreaterEqual(ocr_res.average_confidence, 65.0)

        parser = LabelFieldParser(ocr_res)
        fields = parser.extract_all()
        self.assertTrue(fields["net_quantity"].found)
        self.assertTrue(fields["mrp"].found)


if __name__ == "__main__":
    unittest.main()
