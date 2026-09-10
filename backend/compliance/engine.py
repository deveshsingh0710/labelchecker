import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from config import RULES_CONFIG_PATH, OCR_CONFIDENCE_THRESHOLD
from ocr.field_parser import ExtractedField


@dataclass
class EvaluationItem:
    rule_id: str
    field: str
    title: str
    status: str  # "PASS", "FAIL", "NEEDS_REVIEW"
    severity: str  # "critical", "major", "minor"
    weight: float
    legal_reference: str
    explanation: str
    remediation: str
    extracted_value: Optional[str]
    ocr_confidence: float
    bounding_box: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "field": self.field,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "weight": self.weight,
            "legal_reference": self.legal_reference,
            "explanation": self.explanation,
            "remediation": self.remediation,
            "extracted_value": self.extracted_value,
            "ocr_confidence": round(self.ocr_confidence, 1),
            "bounding_box": self.bounding_box,
        }


@dataclass
class ComplianceSummary:
    overall_score: float
    compliance_status: str  # "COMPLIANT", "PARTIALLY_COMPLIANT", "NON_COMPLIANT"
    total_rules: int
    total_passed: int
    total_failed: int
    total_needs_review: int
    items: List[EvaluationItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 1),
            "compliance_status": self.compliance_status,
            "total_rules": self.total_rules,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_needs_review": self.total_needs_review,
            "items": [item.to_dict() for item in self.items],
        }


class ComplianceEngine:
    """
    Generic rule-based compliance engine driven by external JSON/YAML rule definitions.
    Implements India's Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    def __init__(self, rules_path: Optional[Path] = None):
        self.rules_path = rules_path or RULES_CONFIG_PATH
        self.ruleset = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if not Path(self.rules_path).exists():
            raise FileNotFoundError(f"Rules definition file not found at {self.rules_path}")
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate(
        self,
        extracted_fields: Dict[str, ExtractedField],
        overall_ocr_confidence: float
    ) -> ComplianceSummary:
        """
        Loops through declarative rules and evaluates extracted fields.
        Applies PASS, FAIL, or NEEDS_REVIEW logic.
        """
        rules = self.ruleset.get("rules", [])
        evaluation_items: List[EvaluationItem] = []

        total_weight = 0.0
        earned_weight = 0.0

        for rule in rules:
            rule_id = rule["rule_id"]
            field_key = rule["field"]
            val_type = rule.get("validation_type", "presence")
            title = rule.get("title", field_key)
            severity = rule.get("severity", "major")
            weight = float(rule.get("weight", 2.0))
            legal_ref = rule.get("legal_reference", "")
            remediation = rule.get("remediation", "")
            format_regex = rule.get("format_regex")

            field_obj = extracted_fields.get(field_key)
            field_found = field_obj.found if field_obj else False
            field_val = field_obj.value if field_obj else None
            field_conf = field_obj.confidence if field_obj else 0.0
            field_bbox = field_obj.bounding_box.to_dict() if (field_obj and field_obj.bounding_box) else None

            status = "FAIL"
            explanation = ""

            # 1. Composite Presence (e.g., Manufacturer OR Packer OR Importer)
            if val_type == "presence_or_composite":
                comp_keys = rule.get("composite_fields", [field_key])
                found_any = False
                matched_val = None
                best_conf = 0.0
                best_bbox = None

                for k in comp_keys:
                    k_obj = extracted_fields.get(k)
                    if k_obj and k_obj.found:
                        found_any = True
                        matched_val = k_obj.value
                        best_conf = max(best_conf, k_obj.confidence)
                        if k_obj.bounding_box:
                            best_bbox = k_obj.bounding_box.to_dict()
                        break

                if found_any:
                    if best_conf < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = f"Declaration detected ('{matched_val[:60]}...') but OCR confidence is {round(best_conf, 1)}%. Please visually verify completeness."
                    else:
                        status = "PASS"
                        explanation = f"Manufacturer/Packer identity and address verified: '{matched_val[:60]}...'."
                    field_val = matched_val
                    field_conf = best_conf
                    field_bbox = best_bbox
                else:
                    if overall_ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = "Manufacturer/packer name and address not detected, but overall image clarity is low. Visual inspection recommended."
                    else:
                        status = "FAIL"
                        explanation = "Mandatory declaration of Manufacturer, Packer, or Importer name and complete address is missing from the label."

            # 2. Net Quantity with Standard Unit
            elif val_type == "format_and_unit":
                if field_found and field_val:
                    details = field_obj.details if field_obj else {}
                    is_std = details.get("is_standard_unit", False)
                    raw_unit = details.get("raw_unit", "")

                    if field_conf < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = f"Net quantity extracted as '{field_val}' with lower OCR confidence ({round(field_conf, 1)}%). Confirm unit and quantity on physical pack."
                    elif is_std:
                        status = "PASS"
                        explanation = f"Net quantity '{field_val}' is declared with a valid standard SI unit/symbol under Rule 6(1)(c)."
                    else:
                        status = "FAIL"
                        explanation = f"Net quantity '{field_val}' uses non-standard unit notation ('{raw_unit}'). Legal Metrology requires approved symbols (e.g. g, kg, ml, l, N)."
                else:
                    if overall_ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = "Net quantity declaration not found, but image readability is reduced."
                    else:
                        status = "FAIL"
                        explanation = "Mandatory Net Quantity declaration is missing from the package."

            # 3. Format Regex Validation (e.g. Date MM/YYYY)
            elif val_type == "format":
                if field_found and field_val:
                    if format_regex and re.search(format_regex, field_val, re.IGNORECASE):
                        if field_conf < OCR_CONFIDENCE_THRESHOLD:
                            status = "NEEDS_REVIEW"
                            explanation = f"Date '{field_val}' extracted in valid format, but OCR confidence is {round(field_conf, 1)}%."
                        else:
                            status = "PASS"
                            explanation = f"Month and year of manufacture declared correctly as '{field_val}'."
                    else:
                        status = "FAIL"
                        explanation = f"Date declaration '{field_val}' does not conform to standard MM/YYYY or Month YYYY format."
                else:
                    if overall_ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = "Month and year of manufacture not clearly detected; review label."
                    else:
                        status = "FAIL"
                        explanation = "Month and year of manufacture or packing is missing."

            # 4. MRP Explicit Tax Inclusion Clause
            elif val_type == "custom_mrp_tax":
                mrp_obj = extracted_fields.get("mrp")
                if mrp_obj and mrp_obj.found:
                    has_taxes = mrp_obj.details.get("has_tax_clause", False)
                    if has_taxes:
                        status = "PASS"
                        explanation = "MRP declaration explicitly includes 'inclusive of all taxes' as mandated by Rule 6(1)(e)."
                    else:
                        if mrp_obj.confidence < OCR_CONFIDENCE_THRESHOLD:
                            status = "NEEDS_REVIEW"
                            explanation = "MRP detected, but 'inclusive of all taxes' clause could not be verified with certainty due to image clarity."
                        else:
                            status = "FAIL"
                            explanation = "MRP is declared without the mandatory 'inclusive of all taxes' or 'incl. of all taxes' phrasing."
                else:
                    status = "FAIL"
                    explanation = "Tax inclusion clause cannot be verified because MRP declaration is missing."

            # 5. Customer Care Mechanism
            elif val_type == "custom_consumer_care":
                care_obj = extracted_fields.get("customer_care_details")
                if care_obj and care_obj.found:
                    details = care_obj.details or {}
                    has_phone = details.get("has_phone", False)
                    has_email = details.get("has_email", False)
                    has_addr = details.get("has_contact_address", False)

                    channels = []
                    if has_phone:
                        channels.append("phone")
                    if has_email:
                        channels.append("email")
                    if has_addr and not (has_phone or has_email):
                        channels.append("address")

                    if care_obj.confidence < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = f"Customer care details detected ({', '.join(channels)}) with OCR confidence {round(care_obj.confidence, 1)}%. Verify contact details."
                    else:
                        status = "PASS"
                        explanation = f"Consumer grievance channel provided via {', '.join(channels)}: '{care_obj.value}'."
                else:
                    if overall_ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = "Consumer care contact details not detected, but OCR confidence is low."
                    else:
                        status = "FAIL"
                        explanation = "Mandatory Consumer Care details (toll-free phone, email, or physical address) are missing."

            # 6. Conditional Imported Origin
            elif val_type == "conditional_imported":
                origin_obj = extracted_fields.get("country_of_origin")
                is_imported = origin_obj.details.get("is_imported_detected", False) if origin_obj else False
                has_country = origin_obj.found and origin_obj.value if origin_obj else False

                if is_imported:
                    if has_country:
                        status = "PASS"
                        explanation = f"Imported commodity country of origin declared as '{origin_obj.value}'."
                    else:
                        status = "FAIL"
                        explanation = "Product is marked as imported, but Country of Origin declaration is missing."
                else:
                    # If domestic or origin declared optionally
                    if has_country:
                        status = "PASS"
                        explanation = f"Country of origin declared as '{origin_obj.value}'."
                    else:
                        # Non-imported domestic product without explicit 'Made in' is compliant with general 2011 rules
                        status = "PASS"
                        explanation = "Product not identified as imported; domestic manufacture inferred from manufacturer address."
                        field_val = "Domestic / Inferred from Mfg"

            # 7. Best Before / Expiry (Conditional for food / perishable)
            elif val_type == "conditional_presence":
                exp_obj = extracted_fields.get("best_before_or_expiry_date")
                if exp_obj and exp_obj.found:
                    status = "PASS"
                    explanation = f"Best before / expiry declared: '{exp_obj.value}'."
                else:
                    # In Legal Metrology, best-before is mandatory for items that may become unfit for human consumption.
                    # We flag as NEEDS_REVIEW if not detected, since non-perishable goods don't require it.
                    status = "NEEDS_REVIEW"
                    explanation = "No expiry or 'best before' date detected. Mandatory for food/perishables; optional for non-food items."

            # 8. Standard Simple Presence
            else:
                if field_found and field_val:
                    if field_conf < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = f"Field detected ('{field_val}') with low OCR confidence ({round(field_conf, 1)}%)."
                    else:
                        status = "PASS"
                        explanation = f"Mandatory declaration '{field_val}' is present and verified."
                else:
                    if overall_ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
                        status = "NEEDS_REVIEW"
                        explanation = f"{title} was not detected, but image text clarity is low."
                    else:
                        status = "FAIL"
                        explanation = f"Mandatory declaration of {title} is missing from the label."

            # Calculate weighted scoring
            total_weight += weight
            if status == "PASS":
                earned_weight += weight
            elif status == "NEEDS_REVIEW":
                earned_weight += weight * 0.5  # 50% provisional credit

            evaluation_items.append(
                EvaluationItem(
                    rule_id=rule_id,
                    field=field_key,
                    title=title,
                    status=status,
                    severity=severity,
                    weight=weight,
                    legal_reference=legal_ref,
                    explanation=explanation,
                    remediation=remediation,
                    extracted_value=field_val,
                    ocr_confidence=field_conf,
                    bounding_box=field_bbox
                )
            )

        # Compute overall score percentage
        overall_score = (earned_weight / total_weight * 100.0) if total_weight > 0 else 0.0

        total_passed = sum(1 for i in evaluation_items if i.status == "PASS")
        total_failed = sum(1 for i in evaluation_items if i.status == "FAIL")
        total_needs_review = sum(1 for i in evaluation_items if i.status == "NEEDS_REVIEW")

        if overall_score >= 85.0 and total_failed == 0:
            compliance_status = "COMPLIANT"
        elif overall_score >= 60.0:
            compliance_status = "PARTIALLY_COMPLIANT"
        else:
            compliance_status = "NON_COMPLIANT"

        return ComplianceSummary(
            overall_score=overall_score,
            compliance_status=compliance_status,
            total_rules=len(evaluation_items),
            total_passed=total_passed,
            total_failed=total_failed,
            total_needs_review=total_needs_review,
            items=evaluation_items
        )
