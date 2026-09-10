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
            r"\b(?:mfd|mfg|mktd|marketed|manufactured|produced)\.?\s*(?:&|and)?\s*(?:packed\s*by|by|at)[:\s\.]+(.*)",
            re.IGNORECASE
        )
        pincode_pattern = re.compile(r"\b\d{6}\b")

        mfg_lines: List[OCRLine] = []
        mfg_text_parts: List[str] = []
        capturing = False

        for idx, line in enumerate(self.ocr.lines):
            text = line.text.strip()
            # Exclude lines that are date declarations
            if re.search(r"\b(mfg|mfd)\s*(?:date|dt|\.)\b", text, re.IGNORECASE):
                continue

            if mfg_pattern.search(text):
                capturing = True
                clean_m = re.search(r"\b((?:mfd|mfg|mktd|marketed|manufactured|produced)\b.*)", text, re.IGNORECASE)
                mfg_lines.append(line)
                mfg_text_parts.append(clean_m.group(1) if clean_m else text)
                continue
            if capturing:
                # Skip ingredient/additive lines
                if re.search(r"\b(ins\s*\d+|ingredients?|flavours?|preservatives?)\b", text, re.IGNORECASE):
                    continue
                # Stop if encountering another distinct declaration or license header
                if re.search(r"\b(mrp|net\s*(?:wt|contents?)|pkg|pkd|customer|consumer|exp|lic|fssai|ssa)\b", text, re.IGNORECASE):
                    break
                mfg_lines.append(line)
                mfg_text_parts.append(text)
                # If we captured pincode and at least 2 lines, good candidate
                if pincode_pattern.search(text) and len(mfg_lines) >= 2:
                    break
                if len(mfg_lines) >= 5:
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

        # Priority 2: Look for known commodity keywords in label lines
        commodity_terms = re.compile(
            r"\b(pan\s*masala|gutkha|roasted\s*almonds|almonds|cookies|dark\s*chocolate|chocolate|biscuits?|tea|coffee|potato\s*chips|chips|namkeen|atta|rice|flour|salt|sugar)\b",
            re.IGNORECASE
        )
        for line in self.ocr.lines:
            tm = commodity_terms.search(line.text)
            if tm:
                term_val = tm.group(0).strip().title()
                return ExtractedField(
                    field_name="commodity_name",
                    value=term_val,
                    raw_text=line.text,
                    confidence=line.confidence,
                    bounding_box=line.box,
                    found=True,
                    details={"explicit_declaration": False, "inferred_from_keyword": True}
                )

        # Fallback: Look at top prominent lines (excluding numbers, legal keywords)
        candidate = None
        for line in self.ocr.lines[:8]:
            t = line.text.strip()
            if len(t) > 3 and not re.search(r"\b(mrp|net|qty|pkg|mfd|exp|rs|tel|batch|lot|date|tax|veg|fssai|lic|clean)\b", t, re.IGNORECASE):
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
        """Parses net quantity value and unit, supporting standard and dual declarations (e.g. aerosols)."""
        instruction_filter = re.compile(
            r"\b(hold|away|distance|spray|shake|direction|caution|warning|inflammable|flammable|apply|avoid|eyes)\b",
            re.IGNORECASE
        )
        net_indicator = re.compile(
            r"\b(?:net\s*(?:contents?|vol\.?|volume|wt\.?|weight|qty\.?|quantity)?|contents?|qty\.?|quantity)\b",
            re.IGNORECASE
        )
        dual_qty_pattern = re.compile(
            r"(\d+(?:[\.,]\d+)?)\s*(ml|mi|m1|m\||rn1|l|ltr|ltrs|liter|litres|litre|g|gm|gms|gram|grams|kg|pieces?|pcs?|units?|N|U)\b\s*(?:[\/\&\|\(]\s*(\d+(?:[\.,]\d+)?)\s*(g|gm|gms|gram|grams|ml|mi|m1|m\||rn1)?)?",
            re.IGNORECASE
        )

        matched_lines: List[OCRLine] = []
        qty_value = None
        qty_unit = None
        secondary_qty = None
        secondary_unit = None
        is_dual = False
        qty_line = None

        def _clean_unit(u: str) -> str:
            u_low = u.lower()
            if u_low in ("mi", "m1", "m|", "rn1"):
                return "ml"
            if u_low in ("gm", "gms", "gram", "grams"):
                return "g"
            if u_low in ("ltr", "ltrs", "liter", "litres", "litre"):
                return "l"
            return u_low

        # Pass 1: Prioritize lines near 'Net' / 'Quantity' indicator
        for idx, line in enumerate(self.ocr.lines):
            if instruction_filter.search(line.text) and not net_indicator.search(line.text):
                continue
            if net_indicator.search(line.text):
                # Check on same line
                m = dual_qty_pattern.search(line.text)
                cand_line = line
                if not m:
                    # Check adjacent lines (+1, +2, -1)
                    for off in (1, 2, -1):
                        t_idx = idx + off
                        if 0 <= t_idx < len(self.ocr.lines):
                            cand = self.ocr.lines[t_idx]
                            if instruction_filter.search(cand.text):
                                continue
                            m2 = dual_qty_pattern.search(cand.text)
                            if m2:
                                m = m2
                                cand_line = cand
                                matched_lines = [line, cand] if off > 0 else [cand, line]
                                break
                else:
                    matched_lines = [line]

                if m:
                    qty_value = m.group(1).replace(",", ".")
                    qty_unit = _clean_unit(m.group(2))
                    qty_line = cand_line

                    # Check secondary declaration (e.g. aerosol 140 ml / 98 g)
                    val2 = m.group(3)
                    unit2 = m.group(4)
                    if val2:
                        val2_clean = val2.replace(",", ".")
                        if not unit2 and qty_unit == "ml":
                            unit2_clean = "g"
                        elif unit2:
                            unit2_clean = _clean_unit(unit2)
                        else:
                            unit2_clean = None

                        if unit2_clean:
                            secondary_qty = val2_clean
                            secondary_unit = unit2_clean
                            is_dual = True
                    break

        # Pass 2: Fallback to lines with standard Legal Metrology SI unit
        # Strictly ignore instruction lines and linear measurements (cm, mm, m)
        if not qty_value:
            for line in self.ocr.lines:
                if instruction_filter.search(line.text):
                    continue
                m = dual_qty_pattern.search(line.text)
                if m:
                    val = m.group(1).replace(",", ".")
                    unit = _clean_unit(m.group(2))
                    if unit in ("cm", "mm", "m"):
                        continue
                    if float(val) in (2024, 2025, 2026):
                        continue
                    qty_value = val
                    qty_unit = unit
                    qty_line = line
                    matched_lines = [line]

                    val2 = m.group(3)
                    unit2 = m.group(4)
                    if val2:
                        val2_clean = val2.replace(",", ".")
                        if not unit2 and qty_unit == "ml":
                            unit2_clean = "g"
                        elif unit2:
                            unit2_clean = _clean_unit(unit2)
                        else:
                            unit2_clean = None
                        if unit2_clean:
                            secondary_qty = val2_clean
                            secondary_unit = unit2_clean
                            is_dual = True
                    break

        found = qty_value is not None
        standard_units = {"g", "kg", "ml", "l", "n", "u", "pcs", "pieces"}
        is_standard_unit = (qty_unit in standard_units) if qty_unit else False

        avg_conf = qty_line.confidence if qty_line else (
            (sum(l.confidence for l in matched_lines) / len(matched_lines)) if matched_lines else 0.0
        )
        merged_box = self._merge_boxes_from_lines(matched_lines) if matched_lines else None
        raw_text_str = " ".join(l.text for l in matched_lines) if matched_lines else None

        if found:
            formatted_val = f"{qty_value} {qty_unit} / {secondary_qty} {secondary_unit}" if is_dual else f"{qty_value} {qty_unit}"
        else:
            formatted_val = None

        return ExtractedField(
            field_name="net_quantity",
            value=formatted_val,
            raw_text=raw_text_str,
            confidence=avg_conf,
            bounding_box=merged_box,
            found=found,
            details={
                "quantity": float(qty_value) if qty_value else None,
                "unit": qty_unit,
                "secondary_quantity": float(secondary_qty) if secondary_qty else None,
                "secondary_unit": secondary_unit,
                "is_standard_unit": is_standard_unit,
                "raw_unit": qty_unit,
                "dual_declaration": is_dual
            }
        )

    def parse_mrp(self) -> ExtractedField:
        """Parses MRP amount and checks for 'inclusive of all taxes' declaration."""
        mrp_indicator_regex = re.compile(
            r"\b(?:m\.?[rl1i]?\.?p\.?|m\.?l\.?r\??|mlr|mrp|max(?:imum)?\s*retail\s*price|rs\.?|inr)\b|₹|rs\.",
            re.IGNORECASE
        )
        tax_regex = re.compile(
            r"(?:incl\.?|inclusive|aincl)\s*(?:of\s*)?(?:all\s*)?taxes|inclusive\s*ofall\s*taxes|incl(?:\.|\s)*taxes|all\s*taxes|taxesya",
            re.IGNORECASE
        )

        matched_line = None
        mrp_amount = None
        has_tax_clause = False
        all_mrp_lines: List[OCRLine] = []

        # 1. Check for tax clause in all lines and raw text
        for line in self.ocr.lines:
            if tax_regex.search(line.text):
                has_tax_clause = True
                if line not in all_mrp_lines:
                    all_mrp_lines.append(line)

        if not has_tax_clause and tax_regex.search(self.ocr.raw_text):
            has_tax_clause = True

        def extract_price(text: str) -> Optional[str]:
            # Do NOT treat batch numbers, licenses, or phone numbers as prices
            if re.search(r"\b(batch|lot|b\.?\s*no|lic|license|fssai|phone|tel)\b", text, re.I):
                return None
            # Remove date patterns (04/2024) and quantities (5g, 250g)
            cleaned = re.sub(r"\b\d{1,2}[\/\.-]\d{2,4}\b", "", text)
            cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*(?:g|gm|gms|kg|ml|l|ltr|pcs|pieces|m|cm)\b", "", cleaned, flags=re.I)
            m = re.search(r"(?:rs\.?|₹|inr)?\s*(\d+(?:[\.,]\d{1,2})?)\b", cleaned, re.I)
            if m:
                val = m.group(1).replace(",", ".")
                num = float(val)
                if 0.5 <= num <= 50000 and num not in (2024, 2025, 2026):
                    return val
            return None

        # 2. Find lines matching MRP indicator or Tax clause
        candidate_indices = [
            i for i, l in enumerate(self.ocr.lines)
            if mrp_indicator_regex.search(l.text) or tax_regex.search(l.text)
        ]

        # Pass A: Look for price on the same line as an MRP indicator
        for idx in candidate_indices:
            l = self.ocr.lines[idx]
            p = extract_price(l.text)
            if p:
                mrp_amount = p
                matched_line = l
                if l not in all_mrp_lines:
                    all_mrp_lines.append(l)
                break

        # Pass B: Look for 2-decimal currency format in nearby lines (within +/- 4 lines of indicator/tax)
        if not mrp_amount and candidate_indices:
            nearby_set = set()
            for c_idx in candidate_indices:
                for off in range(-4, 5):
                    t_idx = c_idx + off
                    if 0 <= t_idx < len(self.ocr.lines):
                        nearby_set.add(t_idx)

            sorted_indices = sorted(nearby_set, key=lambda i: min(abs(i - c) for c in candidate_indices))

            for idx in sorted_indices:
                l = self.ocr.lines[idx]
                if re.search(r"\b(batch|lot|b\.?\s*no|lic|license|fssai|ins|date|dt|mfg|exp)\b", l.text, re.I):
                    continue
                m_dec = re.search(r"\b(\d+\.\d{2})\b", l.text)
                if m_dec:
                    val = m_dec.group(1)
                    num = float(val)
                    if 0.5 <= num <= 50000 and num not in (2024, 2025, 2026):
                        mrp_amount = val
                        matched_line = l
                        if l not in all_mrp_lines:
                            all_mrp_lines.append(l)
                        break

        # Pass C: Look for standard 2-decimal currency amount e.g. 10.00 anywhere on label
        if not mrp_amount:
            for l in self.ocr.lines:
                if re.search(r"\b(batch|lot|b\.?\s*no|lic|license|fssai|ins|date|dt|mfg|exp)\b", l.text, re.I):
                    continue
                m_dec = re.search(r"\b(\d+\.\d{2})\b", l.text)
                if m_dec:
                    val = m_dec.group(1)
                    num = float(val)
                    if 0.5 <= num <= 50000 and num not in (2024, 2025, 2026):
                        mrp_amount = val
                        matched_line = l
                        if l not in all_mrp_lines:
                            all_mrp_lines.append(l)
                        break

        # Pass D: Look across lines with explicit ₹ or Rs
        if not mrp_amount:
            for l in self.ocr.lines:
                if re.search(r"₹|rs\.", l.text, re.I):
                    p = extract_price(l.text)
                    if p:
                        mrp_amount = p
                        matched_line = l
                        if l not in all_mrp_lines:
                            all_mrp_lines.append(l)
                        break

        # Pass E: Fallback to general price number in nearby lines
        if not mrp_amount and candidate_indices:
            for idx in sorted_indices:
                l = self.ocr.lines[idx]
                p = extract_price(l.text)
                if p:
                    mrp_amount = p
                    matched_line = l
                    if l not in all_mrp_lines:
                        all_mrp_lines.append(l)
                    break

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
        matched_lines: List[OCRLine] = []

        # Pass 1: Pattern on the same line
        for line in self.ocr.lines:
            m = date_pattern.search(line.text)
            if m:
                extracted_date = m.group(1).strip()
                matched_line = line
                matched_lines.append(line)
                break

        # Pass 2: Line has MFG/PKD keyword, date is on same or next 1-2 lines
        if not extracted_date:
            for idx, line in enumerate(self.ocr.lines):
                if re.search(r"\b(mfd|mfg|pkd|packed)\b", line.text, re.IGNORECASE) and not re.search(r"\b(by|at|ltd|pvt)\b", line.text, re.IGNORECASE):
                    matched_lines.append(line)
                    for off in range(3):
                        if idx + off < len(self.ocr.lines):
                            cand_line = self.ocr.lines[idx + off]
                            m = general_date_pattern.search(cand_line.text)
                            if m:
                                extracted_date = m.group(0)
                                matched_line = cand_line
                                if cand_line not in matched_lines:
                                    matched_lines.append(cand_line)
                                break
                    if extracted_date:
                        break

        # Pass 3: Look for standalone MM/YYYY or MM-YYYY date (excluding expiry and license lines)
        if not extracted_date:
            for line in self.ocr.lines:
                if re.search(r"\b(exp|use\s*by|best\s*before|valid|lic|no|mrp)\b", line.text, re.IGNORECASE):
                    continue
                m = general_date_pattern.search(line.text)
                if m:
                    extracted_date = m.group(0)
                    matched_line = line
                    matched_lines.append(line)
                    break

        found = extracted_date is not None
        avg_conf = (sum(l.confidence for l in matched_lines) / len(matched_lines)) if matched_lines else 0.0

        return ExtractedField(
            field_name="manufacture_date",
            value=extracted_date,
            raw_text=" | ".join(l.text for l in matched_lines) if matched_lines else (matched_line.text if matched_line else None),
            confidence=avg_conf,
            bounding_box=self._merge_boxes_from_lines(matched_lines) if matched_lines else None,
            found=found,
            details={"format_valid": found}
        )

    def parse_best_before(self) -> ExtractedField:
        """Parses expiry date or best before statement."""
        pattern = re.compile(
            r"\b(?:best\s*before|use\s*by|use\s*before|\bexp(?:\.|\s*date|\s*d)?|expiry)\b[:\s\.\-]*(\b(?:0[1-9]|1[0-2])[\/\.\-](?:20\d{2}|\d{2})\b|.+)?",
            re.IGNORECASE
        )
        date_pattern = re.compile(r"\b(0[1-9]|1[0-2])[\/\.\-](20\d{2}|\d{2})\b")
        instruction_filter = re.compile(r"\b(hold|away|spray|shake|direction|caution|warning|inflammable|flammable|expose|heat|sun)\b", re.IGNORECASE)

        matched_line = None
        extracted_val = None
        matched_lines: List[OCRLine] = []

        for idx, line in enumerate(self.ocr.lines):
            # Skip warning / flammability lines (e.g. 'expose to sun')
            if instruction_filter.search(line.text) and not re.search(r"\b(best\s*before|use\s*by|use\s*before)\b", line.text, re.IGNORECASE):
                continue

            m = pattern.search(line.text)
            if m:
                raw_v = (m.group(1) or "").strip()

                # Check if raw_v contains MM/YYYY date
                dm = date_pattern.search(raw_v)
                if dm:
                    extracted_val = dm.group(0)
                    matched_lines.append(line)
                    matched_line = line
                    break

                # If raw_v is empty or just 'Date', check next line
                if not raw_v or raw_v.lower() == "date":
                    if idx + 1 < len(self.ocr.lines):
                        next_line = self.ocr.lines[idx + 1]
                        dm2 = date_pattern.search(next_line.text)
                        if dm2:
                            extracted_val = dm2.group(0)
                            matched_lines.extend([line, next_line])
                            matched_line = line
                            break
                        # Also check duration e.g. '12 months'
                        dur_m = re.search(r"(\d+\s*(?:months?|days?|years?)(?:\s*from\s*[a-z]+)?)", next_line.text, re.I)
                        if dur_m:
                            extracted_val = dur_m.group(1)
                            matched_lines.extend([line, next_line])
                            matched_line = line
                            break

                if raw_v and raw_v.lower() != "date":
                    # If raw_v contains safety instructions like 'sun', 'heat', ignore as false positive
                    if re.search(r"\b(sun|heat|flame|fire|puncture|eyes|children)\b", raw_v, re.IGNORECASE):
                        continue
                    clean_v = re.sub(r"^(?:date[:\s\.\-]*)", "", raw_v, flags=re.I).strip()
                    extracted_val = clean_v or raw_v
                    matched_lines.append(line)
                    matched_line = line
                    break

        found = extracted_val is not None
        avg_conf = (sum(l.confidence for l in matched_lines) / len(matched_lines)) if matched_lines else 0.0

        return ExtractedField(
            field_name="best_before_or_expiry_date",
            value=extracted_val,
            raw_text=" | ".join(l.text for l in matched_lines) if matched_lines else None,
            confidence=avg_conf,
            bounding_box=self._merge_boxes_from_lines(matched_lines) if matched_lines else None,
            found=found,
            details={}
        )

    def parse_customer_care(self) -> ExtractedField:
        """Parses consumer care phone, email, and address."""
        phone_pattern = re.compile(
            r"(?:toll[\s\-]?free|phone|tel|call|contact|no\.?)[:\s\.]*([+]?[\d\s\-]{7,15})|\b1800[\s\-]?\d*\b",
            re.IGNORECASE
        )
        email_pattern = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
        care_keyword_pattern = re.compile(
            r"\b(customer\s*car[ei]|consumer\s*car[ei]|feedback|queries|complaints|contact\s*customer)\b",
            re.IGNORECASE
        )

        phone = None
        email = None
        care_lines: List[OCRLine] = []

        for idx, line in enumerate(self.ocr.lines):
            t = line.text
            has_care = bool(care_keyword_pattern.search(t))
            m_phone = phone_pattern.search(t)
            m_email = email_pattern.search(t)

            if m_phone and not phone:
                phone = m_phone.group(0).strip()
            if m_email and not email:
                email = m_email.group(1).strip()

            if has_care or m_phone or m_email:
                if line not in care_lines:
                    care_lines.append(line)
                # Check adjacent line (+1) for toll-free number or email
                if idx + 1 < len(self.ocr.lines):
                    cand = self.ocr.lines[idx + 1]
                    cand_phone = phone_pattern.search(cand.text)
                    cand_email = email_pattern.search(cand.text)
                    if cand_phone or cand_email or any(w in cand.text.lower() for w in ["toll", "free", "1800", "no."]):
                        if cand not in care_lines:
                            care_lines.append(cand)
                        if cand_phone and not phone:
                            phone = cand_phone.group(0).strip()
                        if cand_email and not email:
                            email = cand_email.group(1).strip()

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
