from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from config import SAMPLES_DIR

def create_sample_labels():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Compliant Label
    img1 = Image.new("RGB", (700, 480), color=(255, 255, 255))
    d1 = ImageDraw.Draw(img1)
    d1.rectangle([(10, 10), (690, 470)], outline=(30, 41, 59), width=3)
    d1.rectangle([(15, 15), (685, 60)], fill=(15, 23, 42))
    
    # Title
    d1.text((30, 24), "HIMALAYAN NATURALS - ORGANIC ROASTED ALMONDS", fill=(255, 255, 255))
    
    # Declarations
    lines1 = [
        "Commodity: Premium Roasted Almonds",
        "Net Quantity: 250 g",
        "MRP: Rs. 350.00 (inclusive of all taxes)",
        "Mfg Date: 08/2026",
        "Best Before: 9 months from packaging",
        "Manufactured & Packed by: Himalayan Naturals Pvt Ltd",
        "Address: Plot 42, Sector 18, Gurugram, Haryana - 122015",
        "Customer Care Toll-Free: 1800-123-9999",
        "Customer Care Email: care@himalayannaturals.in",
        "Country of Origin: India"
    ]
    y = 80
    for line in lines1:
        d1.text((30, y), line, fill=(15, 23, 42))
        y += 36

    p1 = SAMPLES_DIR / "sample_compliant.png"
    img1.save(p1)

    # 2. Non-Compliant Label (Violations: non-standard unit 'gms', missing 'inclusive of taxes', missing customer care, invalid date format)
    img2 = Image.new("RGB", (700, 420), color=(255, 255, 255))
    d2 = ImageDraw.Draw(img2)
    d2.rectangle([(10, 10), (690, 410)], outline=(185, 28, 28), width=3)
    d2.rectangle([(15, 15), (685, 60)], fill=(153, 27, 27))
    d2.text((30, 24), "CHOCO CRUNCH COOKIES", fill=(255, 255, 255))

    lines2 = [
        "Product: Choco Crunch Cookies",
        "Net Weight: 200 gms",  # Violation: 'gms' instead of standard 'g'
        "MRP: Rs. 65.00",        # Violation: missing 'inclusive of all taxes'
        "Mfg Date: 2026",        # Violation: missing month
        "Best Before: 6 Months",
        "Mfd by: Sweet Delights Bakeries, Mumbai" # Incomplete address, missing pincode, missing customer care
    ]
    y = 85
    for line in lines2:
        d2.text((30, y), line, fill=(15, 23, 42))
        y += 42

    p2 = SAMPLES_DIR / "sample_violations.png"
    img2.save(p2)

    # 3. Imported Label
    img3 = Image.new("RGB", (720, 500), color=(255, 255, 255))
    d3 = ImageDraw.Draw(img3)
    d3.rectangle([(10, 10), (710, 490)], outline=(14, 116, 144), width=3)
    d3.rectangle([(15, 15), (705, 60)], fill=(8, 145, 178))
    d3.text((30, 24), "ALPINE SUPREME - 85% DARK CHOCOLATE", fill=(255, 255, 255))

    lines3 = [
        "Commodity: Dark Chocolate Bar",
        "Country of Origin: Switzerland",
        "Net Quantity: 100 g",
        "MRP: Rs. 420.00 (inclusive of all taxes)",
        "Date of Import: 07/2026",
        "Best Before: 18 months from packaging",
        "Imported & Marketed by: Global Confectionery Importers LLP",
        "Address: Unit 12, Connaught Place, New Delhi - 110001",
        "Consumer Care Tel: +91-11-23456789",
        "Consumer Care Email: support@globalimporters.in"
    ]
    y = 80
    for line in lines3:
        d3.text((30, y), line, fill=(15, 23, 42))
        y += 38

    p3 = SAMPLES_DIR / "sample_imported.png"
    img3.save(p3)

    print("Sample labels generated successfully:")
    print(f" - {p1}")
    print(f" - {p2}")
    print(f" - {p3}")

if __name__ == "__main__":
    create_sample_labels()
