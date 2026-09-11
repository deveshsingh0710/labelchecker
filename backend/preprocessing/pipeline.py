import os
import time
import logging
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional
from pathlib import Path

import cv2
import numpy as np

from config import (
    MAX_IMAGE_DIMENSION,
    MIN_IMAGE_DIMENSION,
    DESKEW_MIN_ANGLE,
    DESKEW_MAX_ANGLE,
)

logger = logging.getLogger("labelcheck.preprocessing")
logging.basicConfig(level=logging.INFO)


@dataclass
class PreprocessingResult:
    preprocessed_path: str
    binarized_path: str
    grayscale_path: str
    adaptive_path: str
    deskew_angle: float
    original_dimensions: Tuple[int, int]  # (width, height)
    preprocessed_dimensions: Tuple[int, int]
    upscaled: bool
    downscaled: bool
    timing_ms: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImagePreprocessor:
    """
    Enhanced OpenCV preprocessing pipeline for packaged commodity labels:
    - Downscales oversized images (> 2000px) to prevent processing bottlenecks
    - 2x upscales low-resolution images (< 1200px) with INTER_CUBIC for OCR character clarity
    - Glare reduction via LAB color space CLAHE
    - Auto-deskew via contour analysis (skipping if angle < 0.5 degrees)
    - Median / Bilateral denoising to remove glossy packaging speckle noise
    - Grayscale conversion and Otsu binarization with polarity correction (dark text on white)
    - Adaptive Gaussian thresholding variant for uneven illumination / shadows
    - Persists intermediate preprocessed images to disk for inspection
    """

    def __init__(self, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)):
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size

    def resize_image_if_needed(self, image: np.ndarray) -> Tuple[np.ndarray, bool, bool]:
        """Caps dimensions to MAX_IMAGE_DIMENSION or upscales low-res images < MIN_IMAGE_DIMENSION."""
        h, w = image.shape[:2]
        longest = max(h, w)
        downscaled = False
        upscaled = False

        if longest > MAX_IMAGE_DIMENSION:
            scale = MAX_IMAGE_DIMENSION / float(longest)
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            downscaled = True
            logger.info(f"Downscaled image from ({w}, {h}) to ({new_w}, {new_h}) [cap: {MAX_IMAGE_DIMENSION}px]")
        elif longest < MIN_IMAGE_DIMENSION:
            # Dynamically upscale using Lanczos4 interpolation to achieve recommended 25-35px character height
            scale = min(3.0, float(MIN_IMAGE_DIMENSION) / float(longest))
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            upscaled = True
            logger.info(f"Upscaled image {scale:.2f}x from ({w}, {h}) to ({new_w}, {new_h}) with INTER_LANCZOS4 for improved OCR resolution")

        return image, downscaled, upscaled

    def auto_deskew(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detect and conservatively correct rotational skew.
        Strictly skips deskewing if detected skew angle is under DESKEW_MIN_ANGLE (~0.5°).
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Dilate text lines horizontally
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        angles = []
        min_area = (w * h) * 0.001
        max_area = (w * h) * 0.90

        for c in contours:
            area = cv2.contourArea(c)
            if min_area < area < max_area:
                rect = cv2.minAreaRect(c)
                rw, rh = rect[1]
                raw_angle = rect[-1]
                ang = 90.0 + raw_angle if rw < rh else raw_angle
                if -DESKEW_MAX_ANGLE <= ang <= DESKEW_MAX_ANGLE and abs(ang) >= 0.3:
                    angles.append(ang)

        # Fallback to un-dilated contours if dilated merged with outer image edges
        if not angles:
            raw_contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            for c in raw_contours:
                area = cv2.contourArea(c)
                if min_area < area < max_area:
                    rect = cv2.minAreaRect(c)
                    rw, rh = rect[1]
                    raw_angle = rect[-1]
                    ang = 90.0 + raw_angle if rw < rh else raw_angle
                    if -DESKEW_MAX_ANGLE <= ang <= DESKEW_MAX_ANGLE and abs(ang) >= 0.3:
                        angles.append(ang)

        if not angles or len(angles) < 2:
            logger.debug("Auto-deskew: insufficient contours for skew angle estimation. Skipping.")
            return image, 0.0

        median_angle = float(np.median(angles))
        # Skip deskewing if detected angle is under ~0.5 degrees or exceeds maximum threshold
        if abs(median_angle) < DESKEW_MIN_ANGLE or abs(median_angle) > DESKEW_MAX_ANGLE:
            logger.info(f"Auto-deskew: angle {median_angle:.2f}° within acceptable limit (< {DESKEW_MIN_ANGLE}°). Skipping rotation.")
            return image, 0.0

        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        deskewed = cv2.warpAffine(
            image,
            rot_mat,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255) if len(image.shape) == 3 else 255
        )
        logger.info(f"Auto-deskew: corrected rotational skew by {median_angle:.2f}°")
        return deskewed, median_angle

    def reduce_glare_and_enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast and balance illumination using CLAHE on luminance channel in LAB."""
        if len(image.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
            return clahe.apply(image)

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
        enhanced_l = clahe.apply(l_channel)
        merged = cv2.merge((enhanced_l, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def denoise_image(self, gray: np.ndarray) -> np.ndarray:
        """Median filter and edge-preserving filter to remove speckle noise from glossy packaging."""
        denoised = cv2.medianBlur(gray, 3)
        return denoised

    def create_binarized_otsu(self, gray: np.ndarray) -> np.ndarray:
        """Applies Otsu's thresholding with polarity correction (ensuring black text on white background)."""
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Check polarity: Tesseract requires dark characters on light background
        white_pixels = np.sum(thresh == 255)
        total_pixels = thresh.size
        if white_pixels < (total_pixels * 0.5):
            # Invert if image is mostly dark background with light text
            thresh = cv2.bitwise_not(thresh)
            logger.debug("Inverted binarized polarity for dark background")
        return thresh

    def create_binarized_adaptive(self, gray: np.ndarray) -> np.ndarray:
        """Applies Adaptive Gaussian thresholding for non-uniform lighting / shadows."""
        # Block size 31 provides a wider neighborhood to prevent eroding delicate character strokes
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
        )
        white_pixels = np.sum(adaptive == 255)
        if white_pixels < (adaptive.size * 0.5):
            adaptive = cv2.bitwise_not(adaptive)
        return adaptive

    def process(self, input_path: str, output_path: str) -> PreprocessingResult:
        """
        Executes full preprocessing pipeline:
        1. Dimension normalization (downscale oversized / upscale low-res)
        2. Glare reduction & contrast enhancement (CLAHE)
        3. Auto-deskew
        4. Denoising
        5. Grayscale & Binarization (Otsu & Adaptive)
        6. Persists intermediate preview, binarized, and grayscale images to disk
        """
        t_start = time.perf_counter()
        timing: Dict[str, float] = {}

        img = cv2.imread(str(input_path))
        if img is None:
            raise ValueError(f"Unable to read image at {input_path}")

        orig_h, orig_w = img.shape[:2]

        # Stage 1: Resize if needed
        t0 = time.perf_counter()
        resized_img, downscaled, upscaled = self.resize_image_if_needed(img)
        timing["resize_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # Stage 2: Glare reduction (CLAHE)
        t0 = time.perf_counter()
        glare_reduced = self.reduce_glare_and_enhance_contrast(resized_img)
        timing["glare_reduction_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # Stage 3: Auto-deskew
        t0 = time.perf_counter()
        deskewed, angle = self.auto_deskew(glare_reduced)
        timing["deskew_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # Stage 4: Visual preview enhancement (unsharp mask for human eye)
        t0 = time.perf_counter()
        gaussian = cv2.GaussianBlur(deskewed, (0, 0), 1.0)
        visual_preview = cv2.addWeighted(deskewed, 1.15, gaussian, -0.15, 0)
        timing["sharpen_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # Stage 5: Grayscale & Denoising for OCR
        t0 = time.perf_counter()
        gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
        clahe_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=self.tile_grid_size).apply(gray)
        denoised_gray = self.denoise_image(clahe_gray)
        timing["grayscale_denoise_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # Stage 6: Binarization (Otsu + Adaptive)
        t0 = time.perf_counter()
        otsu_binarized = self.create_binarized_otsu(denoised_gray)
        adaptive_binarized = self.create_binarized_adaptive(denoised_gray)
        timing["binarization_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # Save all intermediate images to disk for inspection
        out_dir = Path(output_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        base_stem = Path(output_path).stem

        # 1. Color preview image (displayed on frontend)
        cv2.imwrite(str(output_path), visual_preview, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # 2. Otsu binarized image (primary OCR target)
        binarized_path = str(out_dir / f"{base_stem}_binarized.png")
        cv2.imwrite(binarized_path, otsu_binarized)

        # 3. High-contrast grayscale image (fallback OCR target)
        grayscale_path = str(out_dir / f"{base_stem}_grayscale.png")
        cv2.imwrite(grayscale_path, denoised_gray)

        # 4. Adaptive binarized image (shadow/glare fallback OCR target)
        adaptive_path = str(out_dir / f"{base_stem}_adaptive.png")
        cv2.imwrite(adaptive_path, adaptive_binarized)

        total_prep_ms = round((time.perf_counter() - t_start) * 1000, 2)
        timing["total_preprocessing_ms"] = total_prep_ms

        final_h, final_w = visual_preview.shape[:2]
        logger.info(
            f"Preprocessing completed in {total_prep_ms}ms: "
            f"Deskew={angle:.2f}°, Upscaled={upscaled}, Downscaled={downscaled}, "
            f"Files saved: [{Path(output_path).name}, {Path(binarized_path).name}]"
        )

        return PreprocessingResult(
            preprocessed_path=str(output_path),
            binarized_path=binarized_path,
            grayscale_path=grayscale_path,
            adaptive_path=adaptive_path,
            deskew_angle=round(angle, 2),
            original_dimensions=(orig_w, orig_h),
            preprocessed_dimensions=(final_w, final_h),
            upscaled=upscaled,
            downscaled=downscaled,
            timing_ms=timing,
            metadata={
                "glare_reduction": "CLAHE (LAB)",
                "denoise": "Median 3x3 filter",
                "binarization": "Otsu + Polarity Inversion",
                "sharpening": "Unsharp Mask",
                "deskew_angle_deg": round(angle, 2),
                "upscaled": upscaled,
                "downscaled": downscaled,
                "binarized_file": Path(binarized_path).name,
                "grayscale_file": Path(grayscale_path).name,
                "adaptive_file": Path(adaptive_path).name,
            }
        )
