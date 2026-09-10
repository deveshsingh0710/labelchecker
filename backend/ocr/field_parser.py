import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .base import OCRResult, OCRLine, BoundingBox


@dataclass
class ExtractedField:
    field_name: str
    value: Optional[str]
    raw_text: Optional[str]
    confidence: float
    bounding_box: Optional[BoundingBox]
    found: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "raw_text": self.raw_text,
            "confidence": round(self.confidence, 1),
            "found": self.found,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "details": self.details,
        }


class LabelFieldParser:
    """
    Parses raw OCR output into structured Legal Metrology packaged commodity fields.
    Extracts text, matched value, confidence score, and bounding boxes.
    """

    def __init__(self, ocr_result: OCRResult):
        self.ocr = ocr_result
        self.img_w = ocr_result.image_width
        self.img_h = ocr_result.image_height

    def _find_lines_matching(self, pattern: re.Pattern) -> List[tuple[OCRLine, re.Match]]:
        matches = []
        for line in self.ocr.lines:
            m = pattern.search(line.text)
            if m:
                matches.append((line, m))
        return matches

    def _merge_boxes_from_lines(self, lines: List[OCRLine]) -> Optional[BoundingBox]:
        boxes = [l.box for l in lines if l.box is not None]
        return BoundingBox.merge(boxes, self.img_w, self.img_h)

    def parse_manufacturer(self) -> tuple[ExtractedField, Optional[ExtractedField]]:
        """Parses manufacturer and packer names/addresses."""
        mfg_pattern = re.compile(
            r"(?:mfd|mfg|manufactured|produced)\s*(?:&|and)?\s*(?:packed\s*by|by|at)?[:\s\.]+(.*)",
            re.IGNORECASE
        )
        pincode_pattern = re.compile(r"\b\d{6}\b")

        mfg_lines: List[OCRLine] = []
        mfg_text_parts: List[str] = []
        capturing = False

        for idx, line in enumerate(self.ocr.lines):
            text = line.text.strip()
            if mfg_pattern.search(text):
                capturing = True
                mfg_lines.append(line)
                mfg_text_parts.append(text)
                continue
            if capturing:
                # Stop if encountering another distinct declaration
                if re.search(r"\b(mrp|net\s*wt|pkg|pkd|packed\s*by|customer|consumer|exp)\b", text, re.IGNORECASE):
                    break
                mfg_lines.append(line)
                mfg_text_parts.append(text)
                # If we captured pincode and at least 2 lines, good candidate
                if pincode_pattern.search(text) and len(mfg_lines) >= 2:
                    break
                if len(mfg_lines) >= 4:
                    break

        mfg_found = len(mfg_lines) > 0
        full_mfg_text = " ".join(mfg_text_parts) if mfg_found else None
        avg_conf = (sum(l.confidence for l in mfg_lines) / len(mfg_lines)) if mfg_lines else 0.0

        mfg_field = ExtractedField(
            field_name="manufacturer_name_and_address",
            value=full_mfg_text,
            raw_text=full_mfg_text,
            confidence=avg_conf,
            bounding_box=self._merge_boxes_from_lines(mfg_lines),
            found=mfg_found,
            details={"has_pincode": bool(pincode_pattern.search(full_mfg_text or ""))}
        )

        # Separate Packer check if present
        packer_pattern = re.compile(r"(?:packed\s*by|pkg\s*by|packer)[:\s\.]+(.*)", re.IGNORECASE)
        packer_lines: List[OCRLine] = []
        for line in self.ocr.lines:
            if packer_pattern.search(line.text) and line not in mfg_lines:
                packer_lines.append(line)

        packer_found = len(packer_lines) > 0
        packer_text = " ".join(l.text for l in packer_lines) if packer_found else None
        p_conf = (sum(l.confidence for l in packer_lines) / len(packer_lines)) if packer_lines else 0.0

        packer_field = ExtractedField(
            field_name="packer_name_and_address",
            value=packer_text,
            raw_text=packer_text,
            confidence=p_conf,
            bounding_box=self._merge_boxes_from_lines(packer_lines),
            found=packer_found,
            details={}
        )

        return mfg_field, packer_field

    def parse_importer(self) -> ExtractedField:
        """Parses importer name and address."""
        pattern = re.compile(r"(?:imported\s*by|importer\s*details|marketed\s*&\s*imported)[:\s\.]+(.*)", re.IGNORECASE)
        lines = []
        for line in self.ocr.lines:
            if pattern.search(line.text):
                lines.append(line)
        found = len(lines) > 0
        text = " ".join(l.text for l in lines) if found else None
        conf = (sum(l.confidence for l in lines) / len(lines)) if lines else 0.0

        return ExtractedField(
            field_name="importer_name_and_address",
            value=text,
            raw_text=text,
            confidence=conf,
            bounding_box=self._merge_boxes_from_lines(lines),
            found=found,
            details={}
        )

    def parse_commodity_name(self) -> ExtractedField:
        """Parses common or generic commodity name."""
        pattern = re.compile(r"(?:commodity|product|item\s*name|product\s*name)[:\s\.]+(.*)", re.IGNORECASE)
        matches = self._find_lines_matching(pattern)
        
        if matches:
            line, m = matches[0]
            val = m.group(1).strip() or line.text.strip()
            return ExtractedField(
                field_name="commodity_name",
                value=val,
                raw_text=line.text,
                confidence=line.confidence,
                bounding_box=line.box,
                found=True,
                details={"explicit_declaration": True}
            )

        # Fallback: Look at top prominent lines (usually line 0 or 1 in blocks)
        candidate = None
        for line in self.ocr.lines[:4]:
            t = line.text.strip()
            # If not pure numbers or legal keyword
            if len(t) > 3 and not re.search(r"\b(mrp|net|pkg|mfd|exp|rs|tel)\b", t, re.IGNORECASE):
                candidate = line
                break

        if candidate:
            return ExtractedField(
                field_name="commodity_name",
                value=candidate.text.strip(),
                raw_text=candidate.text,
                confidence=candidate.confidence,
                bounding_box=candidate.box,
                found=True,
                details={"explicit_declaration": False, "inferred_from_header": True}
            )

        return ExtractedField(
            field_name="commodity_name",
            value=None,
            raw_text=None,
            confidence=0.0,
            bounding_box=None,
            found=False,
            details={}
        )

    def parse_net_quantity(self) -> ExtractedField:
        """Parses net quantity value and unit."""
        # Standard Legal Metrology units: g, kg, ml, l, cm, m, N, U, pieces
        regex = re.compile(
            r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity)?[:\s\.]*)?(\d+(?:[\.,]\d+)?)\s*[\.\s]*(kg|g|gm|gms|gram|grams|ml|l|ltr|ltrs|liter|litres|litre|m|cm|mm|pieces?|pcs?|units?|N|U|9)\b",
            re.IGNORECASE
        )

        matched_line = None
        qty_value = None
        qty_unit = None

        for line in self.ocr.lines:
            m = regex.search(line.text)
            if m:
                val = m.group(1).replace(",", ".")
                unit = m.group(2).lower()
                # Tesseract frequently mistakes small lowercase 'g' for '9'
                if unit == "9" and re.search(r"net", line.text, re.I):
                    unit = "g"
                qty_value = val
                qty_unit = unit
                matched_line = line
                break

        found = matched_line is not None
        # Legal Metrology standard symbols: g, kg, ml, l, cm, m, N, U
        standard_units = {"g", "kg", "ml", "l", "m", "cm", "n", "u"}
        is_standard_unit = (qty_unit in standard_units) if qty_unit else False

        return ExtractedField(
            field_name="net_quantity",
            value=f"{qty_value} {qty_unit}" if found else None,
            raw_text=matched_line.text if matched_line else None,
            confidence=matched_line.confidence if matched_line else 0.0,
            bounding_box=matched_line.box if matched_line else None,
            found=found,
            details={
                "quantity": float(qty_value) if qty_value else None,
                "unit": qty_unit,
                "is_standard_unit": is_standard_unit,
                "raw_unit": qty_unit
            }
        )

    def parse_mrp(self) -> ExtractedField:
        """Parses MRP amount and checks for 'inclusive of all taxes' declaration."""
        # Detect numeric price (accounting for 'Rs', 'Ps', '₹', 'INR')
        mrp_regex = re.compile(
            r"(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price|rs\.?|ps\.?|inr|₹)?[:\s\.]*(?:rs\.?|ps\.?|inr|₹)?\s*(\d+(?:[\.,]\d{1,2})?)",
            re.IGNORECASE
        )
        tax_regex = re.compile(
            r"(?:incl\.?|inclusive)\s*(?:of\s*)?(?:all\s*)?taxes|inclusive\s*ofall\s*taxes|incl(?:\.|\s)*taxes|all\s*taxes",
            re.IGNORECASE
        )

        matched_line = None
        mrp_amount = None
        has_tax_clause = False
        all_mrp_lines = []

        # First search explicitly for lines containing 'MRP' or '₹' or 'Rs'
        for line in self.ocr.lines:
            text = line.text
            if re.search(r"\b(mrp|m\.r\.p|retail\s*price)\b|₹|rs\.|ps\.", text, re.IGNORECASE):
                all_mrp_lines.append(line)
                m = mrp_regex.search(text)
                if m and mrp_amount is None:
                    num_str = m.group(1).replace(",", ".")
                    # Exclude dates or pincodes
                    if len(num_str) <= 7 and float(num_str) > 0 and float(num_str) != 2026:
                        mrp_amount = num_str
                        matched_line = line
                if tax_regex.search(text):
                    has_tax_clause = True

        # Check full raw text if tax clause is in an adjacent line
        if not has_tax_clause and tax_regex.search(self.ocr.raw_text):
            has_tax_clause = True
            for l in self.ocr.lines:
                if tax_regex.search(l.text) and l not in all_mrp_lines:
                    all_mrp_lines.append(l)

        found = mrp_amount is not None
        avg_conf = matched_line.confidence if matched_line else (
            (sum(l.confidence for l in all_mrp_lines) / len(all_mrp_lines)) if all_mrp_lines else 0.0
        )

        merged_box = self._merge_boxes_from_lines(all_mrp_lines) if all_mrp_lines else (
            matched_line.box if matched_line else None
        )

        return ExtractedField(
            field_name="mrp",
            value=f"₹{mrp_amount}" if found else None,
            raw_text=" | ".join(l.text for l in all_mrp_lines) if all_mrp_lines else (matched_line.text if matched_line else None),
            confidence=avg_conf,
            bounding_box=merged_box,
            found=found,
            details={
                "amount": float(mrp_amount) if mrp_amount else None,
                "has_tax_clause": has_tax_clause,
                "tax_declaration": "inclusive of all taxes" if has_tax_clause else "missing"
            }
        )

    def parse_manufacture_date(self) -> ExtractedField:
        """Parses month and year of manufacture/packing."""
        date_pattern = re.compile(
            r"(?:mfd|mfg|pkd|packed|date\s*of\s*mfg)[:\s\.]*(\b(?:0[1-9]|1[0-2]|[A-Za-z]{3,9})[\/\.\-\s]+(?:\d{4}|\d{2})\b)",
            re.IGNORECASE
        )
        general_date_pattern = re.compile(
            r"\b(0[1-9]|1[0-2])[\/\.\-](20\d{2}|\d{2})\b"
        )

        matched_line = None
        extracted_date = None

        for line in self.ocr.lines:
            m = date_pattern.search(line.text)
            if m:
                extracted_date = m.group(1)
                matched_line = line
                break

        if not extracted_date:
            # Look for lines mentioning MFG/PKD followed by date format
            for line in self.ocr.lines:
                if re.search(r"\b(mfd|mfg|pkd|packed)\b", line.text, re.IGNORECASE):
                    m = general_date_pattern.search(line.text)
                    if m:
                        extracted_date = m.group(0)
                        matched_line = line
                        break

        found = extracted_date is not None
        return ExtractedField(
            field_name="manufacture_date",
            value=extracted_date,
            raw_text=matched_line.text if matched_line else None,
            confidence=matched_line.confidence if matched_line else 0.0,
            bounding_box=matched_line.box if matched_line else None,
            found=found,
            details={"format_valid": found}
        )

    def parse_best_before(self) -> ExtractedField:
        """Parses expiry date or best before statement."""
        pattern = re.compile(
            r"(?:best\s*before|use\s*by|exp(?:\.|\s*date)?|expiry)[:\s\.]*(.+)",
            re.IGNORECASE
        )

        matched_line = None
        extracted_val = None

        for line in self.ocr.lines:
            m = pattern.search(line.text)
            if m:
                extracted_val = m.group(1).strip() or line.text.strip()
                matched_line = line
                break

        found = matched_line is not None
        return ExtractedField(
            field_name="best_before_or_expiry_date",
            value=extracted_val,
            raw_text=matched_line.text if matched_line else None,
            confidence=matched_line.confidence if matched_line else 0.0,
            bounding_box=matched_line.box if matched_line else None,
            found=found,
            details={}
        )

    def parse_customer_care(self) -> ExtractedField:
        """Parses consumer care phone, email, and address."""
        phone_pattern = re.compile(
            r"(?:toll[\s\-]?free|phone|tel|call|contact)[:\s\.]*([+]?[\d\s\-]{8,15})|\b1800[\s\-]?\d{3}[\s\-]?\d{3,4}\b",
            re.IGNORECASE
        )
        email_pattern = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
        care_keyword_pattern = re.compile(r"\b(customer\s*care|consumer\s*care|feedback|queries|complaints)\b", re.IGNORECASE)

        phone = None
        email = None
        care_lines: List[OCRLine] = []

        for line in self.ocr.lines:
            t = line.text
            has_care = care_keyword_pattern.search(t)
            m_phone = phone_pattern.search(t)
            m_email = email_pattern.search(t)

            if m_phone and not phone:
                phone = m_phone.group(0).strip()
            if m_email and not email:
                email = m_email.group(1).strip()

            if has_care or m_phone or m_email:
                care_lines.append(line)

        found = (phone is not None) or (email is not None) or (len(care_lines) > 0)
        avg_conf = (sum(l.confidence for l in care_lines) / len(care_lines)) if care_lines else 0.0

        summary = []
        if phone:
            summary.append(f"Phone: {phone}")
        if email:
            summary.append(f"Email: {email}")
        if not summary and care_lines:
            summary.append(care_lines[0].text)

        return ExtractedField(
            field_name="customer_care_details",
            value=" | ".join(summary) if summary else None,
            raw_text=" | ".join(l.text for l in care_lines) if care_lines else None,
            confidence=avg_conf,
            bounding_box=self._merge_boxes_from_lines(care_lines),
            found=found,
            details={
                "has_phone": phone is not None,
                "phone": phone,
                "has_email": email is not None,
                "email": email,
                "has_contact_address": len(care_lines) > 0
            }
        )

    def parse_country_of_origin(self) -> ExtractedField:
        """Parses country of origin declaration (especially required for imported commodities)."""
        pattern = re.compile(
            r"(?:country\s*of\s*origin|made\s*in|product\s*of)[:\s\.]*([A-Za-z\s]+)",
            re.IGNORECASE
        )
        matched_line = None
        country = None

        for line in self.ocr.lines:
            m = pattern.search(line.text)
            if m:
                country = m.group(1).strip()
                matched_line = line
                break

        # Check if product mentions imported
        is_imported = bool(re.search(r"\b(imported|importer)\b", self.ocr.raw_text, re.IGNORECASE))

        found = country is not None
        return ExtractedField(
            field_name="country_of_origin",
            value=country,
            raw_text=matched_line.text if matched_line else None,
            confidence=matched_line.confidence if matched_line else 0.0,
            bounding_box=matched_line.box if matched_line else None,
            found=found,
            details={
                "country": country,
                "is_imported_detected": is_imported
            }
        )

    def extract_all(self) -> Dict[str, ExtractedField]:
        """Executes all field parsers and returns structured dictionary."""
        mfg, packer = self.parse_manufacturer()
        importer = self.parse_importer()
        commodity = self.parse_commodity_name()
        net_qty = self.parse_net_quantity()
        mrp = self.parse_mrp()
        mfg_date = self.parse_manufacture_date()
        expiry = self.parse_best_before()
        care = self.parse_customer_care()
        origin = self.parse_country_of_origin()

        return {
            "manufacturer_name_and_address": mfg,
            "packer_name_and_address": packer,
            "importer_name_and_address": importer,
            "commodity_name": commodity,
            "net_quantity": net_qty,
            "mrp": mrp,
            "manufacture_date": mfg_date,
            "best_before_or_expiry_date": expiry,
            "customer_care_details": care,
            "country_of_origin": origin,
        }
