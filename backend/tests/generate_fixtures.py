import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import cv2

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

def generate_base_label() -> Image.Image:
    """Creates a standardized legal metrology test label."""
    img = Image.new("RGB", (800, 520), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Border & Header Banner
    d.rectangle([(10, 10), (790, 510)], outline=(15, 23, 42), width=3)
    d.rectangle([(15, 15), (785, 65)], fill=(15, 23, 42))
    d.text((30, 28), "PURE NATURE FOODS - 100% ORGANIC RAW HONEY", fill=(255, 255, 255))

    # Standard declarations
    lines = [
        "Commodity: Organic Raw Honey",
        "Net Quantity: 500 g",
        "MRP: Rs. 299.00 (inclusive of all taxes)",
        "Mfg Date: 09/2026",
        "Best Before: 24 months from packaging",
        "Manufactured & Packed by: Pure Nature Foods Pvt Ltd",
        "Address: Plot 15, Industrial Estate, Solan, HP - 173212",
        "Customer Care Toll-Free: 1800-456-7890",
        "Customer Care Email: support@purenature.in",
        "Country of Origin: India",
    ]

    y = 85
    for line in lines:
        d.text((35, y), line, fill=(15, 23, 42))
        y += 38

    return img

def create_sharp_fixture(base_img: Image.Image) -> Path:
    out = FIXTURES_DIR / "fixture_sharp.png"
    base_img.save(out)
    return out

def create_angled_fixture(base_img: Image.Image, angle_deg: float = 3.0) -> Path:
    """Rotates label by angle_deg with clean white background."""
    out = FIXTURES_DIR / "fixture_angled.png"
    rotated = base_img.rotate(-angle_deg, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    rotated.save(out)
    return out

def create_low_light_fixture(base_img: Image.Image) -> Path:
    """Simulates low-light / underexposed condition with low contrast."""
    out = FIXTURES_DIR / "fixture_low_light.png"
    arr = np.array(base_img, dtype=np.float32)
    # Dim by 60% and add slight noise
    dimmed = arr * 0.40
    noise = np.random.normal(0, 3, dimmed.shape)
    dimmed = np.clip(dimmed + noise, 0, 255).astype(np.uint8)
    Image.fromarray(dimmed).save(out)
    return out

def create_glossy_glare_fixture(base_img: Image.Image) -> Path:
    """Simulates bright specular glare reflection hotspot across packaging."""
    out = FIXTURES_DIR / "fixture_glossy_glare.png"
    arr = np.array(base_img, dtype=np.float32)
    h, w = arr.shape[:2]

    # Create radial glare gradient centered at (w*0.5, h*0.4)
    cx, cy = int(w * 0.5), int(h * 0.4)
    y_idx, x_idx = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x_idx - cx)**2 + (y_idx - cy)**2)
    max_radius = 200.0
    glare_intensity = np.clip(1.0 - (dist_from_center / max_radius), 0.0, 1.0) * 140.0
    glare_3d = np.repeat(glare_intensity[:, :, np.newaxis], 3, axis=2)

    glared = np.clip(arr + glare_3d, 0, 255).astype(np.uint8)
    Image.fromarray(glared).save(out)
    return out

def generate_all_fixtures():
    base = generate_base_label()
    p1 = create_sharp_fixture(base)
    p2 = create_angled_fixture(base, 3.0)
    p3 = create_low_light_fixture(base)
    p4 = create_glossy_glare_fixture(base)

    print("Test fixtures successfully generated:")
    print(f" - Sharp: {p1}")
    print(f" - Angled (+3.0 deg): {p2}")
    print(f" - Low-light: {p3}")
    print(f" - Glossy / Glare: {p4}")

if __name__ == "__main__":
    generate_all_fixtures()
