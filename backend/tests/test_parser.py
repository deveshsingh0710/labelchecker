from ocr.base import OCRResult, OCRLine, BoundingBox
from ocr.field_parser import LabelFieldParser

def test_field_parser_regex():
    lines = [
        OCRLine("HIMALAYAN NATURALS", 90.0, BoundingBox(10, 10, 100, 20, 500, 500)),
        OCRLine("Commodity: Roasted Almonds", 92.0, BoundingBox(10, 40, 200, 20, 500, 500)),
        OCRLine("Net Quantity: 250 g", 95.0, BoundingBox(10, 70, 150, 20, 500, 500)),
        OCRLine("MRP: Rs. 350.00 (inclusive of all taxes)", 91.0, BoundingBox(10, 100, 250, 20, 500, 500)),
        OCRLine("Mfg Date: 08/2026", 94.0, BoundingBox(10, 130, 120, 20, 500, 500)),
        OCRLine("Best Before: 9 months from pkd", 89.0, BoundingBox(10, 160, 180, 20, 500, 500)),
        OCRLine("Customer Care: 1800-123-9999", 93.0, BoundingBox(10, 190, 190, 20, 500, 500)),
        OCRLine("Mfd by: Himalayan Naturals Pvt Ltd, 122015", 90.0, BoundingBox(10, 220, 300, 20, 500, 500)),
    ]
    raw = "\n".join(l.text for l in lines)
    ocr = OCRResult(raw, 92.0, 500, 500, lines=lines)
    parser = LabelFieldParser(ocr)
    fields = parser.extract_all()

    assert fields["commodity_name"].found is True
    assert fields["commodity_name"].value == "Roasted Almonds"
    assert fields["net_quantity"].found is True
    assert fields["net_quantity"].details["is_standard_unit"] is True
    assert fields["mrp"].found is True
    assert fields["mrp"].details["has_tax_clause"] is True
    assert fields["manufacture_date"].found is True
    assert fields["manufacture_date"].value == "08/2026"
    assert fields["customer_care_details"].found is True

def test_field_parser_multiline_pouch():
    lines = [
        OCRLine("Net", 85.0, BoundingBox(10, 10, 50, 20, 500, 500)),
        OCRLine("5g", 91.0, BoundingBox(70, 10, 50, 20, 500, 500)),
        OCRLine("PAN MASALA", 88.0, BoundingBox(10, 40, 120, 20, 500, 500)),
        OCRLine("MLR?", 75.0, BoundingBox(10, 70, 60, 20, 500, 500)),
        OCRLine("Aincl. of all taxesya", 82.0, BoundingBox(10, 100, 180, 20, 500, 500)),
        OCRLine("10.00", 96.0, BoundingBox(10, 130, 80, 20, 500, 500)),
        OCRLine("Batch No. : B0424", 85.0, BoundingBox(10, 160, 150, 20, 500, 500)),
        OCRLine("Mfg. Date : 04/2024", 80.0, BoundingBox(10, 190, 140, 20, 500, 500)),
        OCRLine("Exp. Date : 03/2025", 83.0, BoundingBox(10, 220, 140, 20, 500, 500)),
        OCRLine("Manufactured & Packed by: RMD Pan Masala Pvt. Ltd.", 90.0, BoundingBox(10, 250, 300, 20, 500, 500)),
        OCRLine("SIDCUL, Haridwar - 249403, Uttarakhand", 88.0, BoundingBox(10, 280, 300, 20, 500, 500)),
    ]
    raw = "\n".join(l.text for l in lines)
    ocr = OCRResult(raw, 86.0, 500, 500, lines=lines)
    parser = LabelFieldParser(ocr)
    fields = parser.extract_all()

    assert fields["net_quantity"].found is True
    assert fields["net_quantity"].value == "5 g"
    assert fields["mrp"].found is True
    assert fields["mrp"].value == "₹10.00"
    assert fields["mrp"].details["has_tax_clause"] is True
    assert fields["manufacture_date"].found is True
    assert fields["manufacture_date"].value == "04/2024"
    assert fields["best_before_or_expiry_date"].found is True
    assert fields["best_before_or_expiry_date"].value == "03/2025"
    assert fields["manufacturer_name_and_address"].found is True
    assert "249403" in fields["manufacturer_name_and_address"].value

def test_field_parser_aerosol_spray():
    lines = [
        OCRLine("DENVER AUTOGRAPH", 92.0, BoundingBox(10, 10, 200, 20, 500, 500)),
        OCRLine("Hold 16 cm away from the body and spray,", 84.0, BoundingBox(10, 40, 300, 20, 500, 500)),
        OCRLine("WARNING: Flammable, Contents under pressure, do not expose to sun OF heat", 82.0, BoundingBox(10, 70, 450, 20, 500, 500)),
        OCRLine("MKTD BY: VANESA CARE PVT. LTD.", 92.0, BoundingBox(10, 100, 250, 20, 500, 500)),
        OCRLine("18, G.F, Pusa Road, New Delhi-110005", 82.0, BoundingBox(10, 130, 280, 20, 500, 500)),
        OCRLine("CONTACT CUSTOMER CARI", 94.0, BoundingBox(10, 160, 200, 20, 500, 500)),
        OCRLine("iC No.: 1800", 73.0, BoundingBox(10, 190, 100, 20, 500, 500)),
        OCRLine("NET CONTENTS:", 96.0, BoundingBox(10, 220, 150, 20, 500, 500)),
        OCRLine("140 mi / 98", 85.0, BoundingBox(10, 250, 120, 20, 500, 500)),
        OCRLine("RS.275.00", 77.0, BoundingBox(10, 280, 100, 20, 500, 500)),
        OCRLine("08/2024", 57.0, BoundingBox(10, 310, 80, 20, 500, 500)),
    ]
    raw = "\n".join(l.text for l in lines)
    ocr = OCRResult(raw, 85.0, 500, 500, lines=lines)
    parser = LabelFieldParser(ocr)
    fields = parser.extract_all()

    # Net quantity must be dual declaration 140 ml / 98 g, NOT 16 cm
    assert fields["net_quantity"].found is True
    assert fields["net_quantity"].value == "140 ml / 98 g"
    assert fields["net_quantity"].details["is_standard_unit"] is True

    # Expiry must NOT match "expose to sun of heat"
    assert fields["best_before_or_expiry_date"].value != "ose to sun OF heat"

    # Manufacturer / Marketer must be found with pincode
    assert fields["manufacturer_name_and_address"].found is True
    assert "VANESA CARE" in fields["manufacturer_name_and_address"].value
    assert fields["manufacturer_name_and_address"].details["has_pincode"] is True

    # Customer care must capture 1800
    assert fields["customer_care_details"].found is True
    assert "1800" in fields["customer_care_details"].value

    # MRP must be Rs 275.00
    assert fields["mrp"].found is True
    assert fields["mrp"].value == "₹275.00"

