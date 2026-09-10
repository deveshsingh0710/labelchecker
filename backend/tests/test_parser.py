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
