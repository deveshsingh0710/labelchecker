import unittest
from compliance import ComplianceEngine
from ocr.field_parser import ExtractedField


class TestComplianceRules(unittest.TestCase):

    def test_rules_loading(self):
        engine = ComplianceEngine()
        self.assertGreaterEqual(len(engine.ruleset.get("rules", [])), 7)

    def test_compliant_evaluation(self):
        engine = ComplianceEngine()
        fields = {
            "manufacturer_name_and_address": ExtractedField("manufacturer_name_and_address", "Himalayan Naturals Pvt Ltd, Gurugram 122015", "...", 95.0, None, True, {"has_pincode": True}),
            "commodity_name": ExtractedField("commodity_name", "Roasted Almonds", "...", 95.0, None, True, {}),
            "net_quantity": ExtractedField("net_quantity", "250 g", "...", 95.0, None, True, {"is_standard_unit": True, "raw_unit": "g"}),
            "mrp": ExtractedField("mrp", "₹350.00", "...", 95.0, None, True, {"has_tax_clause": True}),
            "manufacture_date": ExtractedField("manufacture_date", "08/2026", "...", 95.0, None, True, {}),
            "best_before_or_expiry_date": ExtractedField("best_before_or_expiry_date", "9 months", "...", 95.0, None, True, {}),
            "customer_care_details": ExtractedField("customer_care_details", "Phone: 1800-123-9999", "...", 95.0, None, True, {"has_phone": True}),
            "country_of_origin": ExtractedField("country_of_origin", "India", "...", 95.0, None, True, {"is_imported_detected": False}),
        }
        summary = engine.evaluate(fields, overall_ocr_confidence=92.0)
        self.assertGreaterEqual(summary.overall_score, 85.0)
        self.assertEqual(summary.compliance_status, "COMPLIANT")
        self.assertEqual(summary.total_failed, 0)

    def test_non_compliant_evaluation(self):
        engine = ComplianceEngine()
        fields = {
            "manufacturer_name_and_address": ExtractedField("manufacturer_name_and_address", None, None, 0.0, None, False, {}),
            "commodity_name": ExtractedField("commodity_name", "Cookies", "...", 90.0, None, True, {}),
            "net_quantity": ExtractedField("net_quantity", "200 gms", "...", 90.0, None, True, {"is_standard_unit": False, "raw_unit": "gms"}),
            "mrp": ExtractedField("mrp", "₹60.00", "...", 90.0, None, True, {"has_tax_clause": False}),
            "manufacture_date": ExtractedField("manufacture_date", "2026", "...", 90.0, None, True, {}),
            "best_before_or_expiry_date": ExtractedField("best_before_or_expiry_date", None, None, 0.0, None, False, {}),
            "customer_care_details": ExtractedField("customer_care_details", None, None, 0.0, None, False, {}),
            "country_of_origin": ExtractedField("country_of_origin", None, None, 0.0, None, False, {"is_imported_detected": False}),
        }
        summary = engine.evaluate(fields, overall_ocr_confidence=85.0)
        self.assertLess(summary.overall_score, 60.0)
        self.assertEqual(summary.compliance_status, "NON_COMPLIANT")
        self.assertGreaterEqual(summary.total_failed, 3)

    def test_low_confidence_triggers_needs_review(self):
        engine = ComplianceEngine()
        fields = {
            "manufacturer_name_and_address": ExtractedField("manufacturer_name_and_address", "Some Blurred Text", "...", 35.0, None, True, {}),
            "commodity_name": ExtractedField("commodity_name", None, None, 0.0, None, False, {}),
            "net_quantity": ExtractedField("net_quantity", "100 g", "...", 40.0, None, True, {"is_standard_unit": True, "raw_unit": "g"}),
            "mrp": ExtractedField("mrp", "₹50", "...", 42.0, None, True, {"has_tax_clause": False}),
            "manufacture_date": ExtractedField("manufacture_date", "05/2026", "...", 38.0, None, True, {}),
            "best_before_or_expiry_date": ExtractedField("best_before_or_expiry_date", None, None, 0.0, None, False, {}),
            "customer_care_details": ExtractedField("customer_care_details", None, None, 0.0, None, False, {}),
            "country_of_origin": ExtractedField("country_of_origin", None, None, 0.0, None, False, {"is_imported_detected": False}),
        }
        summary = engine.evaluate(fields, overall_ocr_confidence=35.0)
        self.assertGreater(summary.total_needs_review, 0)


if __name__ == "__main__":
    unittest.main()
