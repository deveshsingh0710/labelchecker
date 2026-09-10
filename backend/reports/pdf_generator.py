import cv2
import html
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from config import REPORTS_DIR


class ComplianceReportGenerator:
    """
    Generates inspector-ready Legal Metrology compliance verification PDF reports.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
        )
        self.subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_LEFT,
        )
        self.h2_style = ParagraphStyle(
            "Heading2Style",
            parent=self.styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
            spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "BodyStyle",
            parent=self.styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        self.table_header_style = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
        self.cell_style = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        self.status_pass_style = ParagraphStyle(
            "StatusPass",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#166534"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
        self.status_fail_style = ParagraphStyle(
            "StatusFail",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#991b1b"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
        self.status_review_style = ParagraphStyle(
            "StatusReview",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#854d0e"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )

    def _create_annotated_image(
        self,
        image_path: str,
        evaluation_items: List[Dict[str, Any]],
        output_path: str
    ) -> str:
        """Draws colored bounding boxes on the label image for visual evidence in the PDF."""
        img = cv2.imread(str(image_path))
        if img is None:
            return image_path

        h, w = img.shape[:2]
        # Colors in BGR
        color_map = {
            "PASS": (46, 204, 113),         # Green
            "FAIL": (46, 46, 231),          # Red
            "NEEDS_REVIEW": (41, 128, 243)  # Amber / Yellow
        }

        overlay = img.copy()

        for item in evaluation_items:
            bbox = item.get("bounding_box")
            if not bbox:
                continue

            bx = int(bbox.get("x", 0))
            by = int(bbox.get("y", 0))
            bw = int(bbox.get("width", 0))
            bh = int(bbox.get("height", 0))

            if bw <= 0 or bh <= 0:
                continue

            status = item.get("status", "NEEDS_REVIEW")
            color = color_map.get(status, (200, 200, 200))

            # Draw transparent rectangle fill
            cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), color, -1)
            # Draw solid border
            cv2.rectangle(img, (bx, by), (bx + bw, by + bh), color, 3)

        # Blend transparent highlight
        cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return str(output_path)

    def generate(
        self,
        verification_data: Dict[str, Any],
        image_path: str,
        output_filename: str = None
    ) -> str:
        """Compiles and builds the PDF compliance report."""
        v_id = verification_data.get("id", "audit")
        if not output_filename:
            output_filename = f"report_{v_id}.pdf"

        report_file_path = REPORTS_DIR / output_filename
        doc = SimpleDocTemplate(
            str(report_file_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        elements = []

        # 1. Header Banner
        header_data = [
            [
                Paragraph("<b>LabelCheck</b> &bull; Legal Metrology Compliance Audit", self.title_style),
                Paragraph(f"<b>Verification ID:</b><br/>{v_id[:8]}...<br/><b>Date:</b> {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}", self.subtitle_style)
            ]
        ]
        header_table = Table(header_data, colWidths=[360, 180])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=15))

        # 2. Score & Executive Summary
        score = verification_data.get("overall_score", 0.0)
        status = verification_data.get("compliance_status", "NON_COMPLIANT")
        total_p = verification_data.get("total_passed", 0)
        total_f = verification_data.get("total_failed", 0)
        total_r = verification_data.get("total_needs_review", 0)

        status_color = colors.HexColor("#166534") if status == "COMPLIANT" else (
            colors.HexColor("#854d0e") if status == "PARTIALLY_COMPLIANT" else colors.HexColor("#991b1b")
        )

        summary_box_data = [
            [
                Paragraph("<b>COMPLIANCE SCORE</b>", self.cell_style),
                Paragraph("<b>AUDIT STATUS</b>", self.cell_style),
                Paragraph("<b>RULES PASSED</b>", self.cell_style),
                Paragraph("<b>VIOLATIONS (FAIL)</b>", self.cell_style),
                Paragraph("<b>NEEDS REVIEW</b>", self.cell_style),
            ],
            [
                Paragraph(f"<font size=16 color='{status_color.hexval()}'><b>{score}%</b></font>", self.cell_style),
                Paragraph(f"<font size=11 color='{status_color.hexval()}'><b>{status.replace('_', ' ')}</b></font>", self.cell_style),
                Paragraph(f"<font size=14 color='#166534'><b>{total_p}</b></font>", self.cell_style),
                Paragraph(f"<font size=14 color='#991b1b'><b>{total_f}</b></font>", self.cell_style),
                Paragraph(f"<font size=14 color='#854d0e'><b>{total_r}</b></font>", self.cell_style),
            ]
        ]
        summary_table = Table(summary_box_data, colWidths=[108, 120, 100, 110, 102])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))

        # 3. Label Visual Evidence
        elements.append(Paragraph("Label Visual Evidence & Bounding-Box Detection", self.h2_style))
        annotated_img_path = REPORTS_DIR / f"annotated_{v_id}.jpg"
        self._create_annotated_image(image_path, verification_data.get("evaluation_results", []), str(annotated_img_path))

        if annotated_img_path.exists():
            try:
                # Scale image nicely to fit printable area (max width 520, max height 220)
                cv_img = cv2.imread(str(annotated_img_path))
                ih, iw = cv_img.shape[:2]
                max_w, max_h = 520, 220
                scale = min(max_w / iw, max_h / ih)
                disp_w = iw * scale
                disp_h = ih * scale

                rl_img = RLImage(str(annotated_img_path), width=disp_w, height=disp_h)
                rl_img.hAlign = "CENTER"
                elements.append(rl_img)
                elements.append(Spacer(1, 12))
            except Exception as e:
                print(f"Warning: Could not embed image into PDF: {e}")

        # 4. Mandatory Declarations Audit Table
        elements.append(Paragraph("Mandatory Declarations Verification Checklist (Rules, 2011)", self.h2_style))
        table_rows = [
            [
                Paragraph("Legal Rule", self.table_header_style),
                Paragraph("Mandatory Field", self.table_header_style),
                Paragraph("Extracted Value", self.table_header_style),
                Paragraph("OCR Conf.", self.table_header_style),
                Paragraph("Severity", self.table_header_style),
                Paragraph("Status", self.table_header_style),
            ]
        ]

        results = verification_data.get("evaluation_results", [])
        for item in results:
            st = item.get("status", "FAIL")
            if st == "PASS":
                st_p = Paragraph("PASS", self.status_pass_style)
            elif st == "NEEDS_REVIEW":
                st_p = Paragraph("REVIEW", self.status_review_style)
            else:
                st_p = Paragraph("FAIL", self.status_fail_style)

            raw_val = item.get("extracted_value")
            if raw_val:
                escaped_val = html.escape(str(raw_val))
                if len(escaped_val) > 42:
                    escaped_val = escaped_val[:39] + "..."
                val_p = Paragraph(escaped_val, self.cell_style)
            else:
                val_p = Paragraph("<font color='#94a3b8'>Not detected</font>", self.cell_style)

            rule_id_esc = html.escape(str(item.get('rule_id', '')))
            leg_ref_esc = html.escape(str(item.get('legal_reference', '')[:32]))
            title_esc = html.escape(str(item.get('title', '')))

            table_rows.append([
                Paragraph(f"<b>{rule_id_esc}</b><br/><font size=7 color='#64748b'>{leg_ref_esc}</font>", self.cell_style),
                Paragraph(f"<b>{title_esc}</b>", self.cell_style),
                val_p,
                Paragraph(f"{round(item.get('ocr_confidence', 0), 1)}%", self.cell_style),
                Paragraph(item.get("severity", "major").upper(), self.cell_style),
                st_p
            ])

        findings_table = Table(table_rows, colWidths=[110, 110, 160, 50, 55, 55])
        findings_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(findings_table)
        elements.append(Spacer(1, 15))

        # 5. Non-Compliance Violations & Remediation Recommendations
        violations = [i for i in results if i.get("status") in ("FAIL", "NEEDS_REVIEW")]
        if violations:
            elements.append(KeepTogether([
                Paragraph("Violations & Remedial Actions Required", self.h2_style),
                Spacer(1, 4)
            ]))
            for v in violations:
                st = v.get("status")
                sev = v.get("severity", "major").upper()
                badge_color = "#991b1b" if st == "FAIL" else "#854d0e"
                v_title = html.escape(str(v.get('title', '')))
                v_ref = html.escape(str(v.get('legal_reference', '')))
                v_expl = html.escape(str(v.get('explanation', '')))
                v_remed = html.escape(str(v.get('remediation', '')))

                v_block = [
                    Paragraph(
                        f"<font color='{badge_color}'><b>[{st}]</b></font> <b>{v_title}</b> ({v_ref}) &bull; <i>Severity: {sev}</i>",
                        self.body_style
                    ),
                    Paragraph(f"<b>Issue:</b> {v_expl}", self.body_style),
                    Paragraph(f"<b>Remediation:</b> {v_remed}", self.body_style),
                    Spacer(1, 6)
                ]
                elements.append(KeepTogether(v_block))

        # 6. Legal Disclaimer & Sign-off
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        disclaimer = (
            "<b>Disclaimer:</b> This report is automatically generated by LabelCheck AI using OCR and rule evaluation "
            "based on the Legal Metrology (Packaged Commodities) Rules, 2011. Results provide technical compliance assistance "
            "and do not constitute formal judicial certification."
        )
        elements.append(Paragraph(disclaimer, self.subtitle_style))

        # Build PDF document
        doc.build(elements)
        return str(report_file_path)
