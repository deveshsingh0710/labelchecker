import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any
from pathlib import Path


@dataclass
class PreprocessingResult:
    preprocessed_path: str
    deskew_angle: float
    original_dimensions: Tuple[int, int]  # (width, height)
    preprocessed_dimensions: Tuple[int, int]
    metadata: Dict[str, Any]


class ImagePreprocessor:
    """
    OpenCV preprocessing pipeline for packaged commodity labels:
    - Glare reduction via LAB color space CLAHE
    - Auto-deskew via minAreaRect on high-density text contours
    - Edge-preserving denoising via bilateral filtering
    - Contrast and sharpness enhancement
    """

    def __init__(self, clip_limit: float = 2.5, tile_grid_size: Tuple[int, int] = (8, 8)):
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size

    def auto_deskew(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Detect and conservatively correct small rotational skew without shearing package photos."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Otsu thresholding after Gaussian blur to isolate text regions
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Dilate text blocks horizontally
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        angles = []
        h, w = image.shape[:2]
        min_area = (w * h) * 0.002
        max_area = (w * h) * 0.2  # ignore entire package contour to avoid package tilt angle

        for c in contours:
            area = cv2.contourArea(c)
            if min_area < area < max_area:
                rect = cv2.minAreaRect(c)
                angle = rect[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                # Only trust small text line skew (within +/- 6 degrees)
                if -6.0 <= angle <= 6.0 and abs(angle) > 0.4:
                    angles.append(angle)

        if not angles or len(angles) < 3:
            return image, 0.0

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5 or abs(median_angle) > 6.0:
            return image, 0.0

        # Rotate image with clean white border, NEVER border replicate
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        deskewed = cv2.warpAffine(
            image,
            rot_mat,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        return deskewed, median_angle

    def reduce_glare_and_enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast and balance illumination using CLAHE on the L channel in LAB."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=self.tile_grid_size)
        enhanced_l = clahe.apply(l_channel)
        
        merged = cv2.merge((enhanced_l, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def denoise_and_sharpen(self, image: np.ndarray) -> np.ndarray:
        """Gentle edge definition enhancement without blurring small font characters."""
        # Subtle unsharp mask preserves fine character details (10-12pt) without blurring thin font strokes
        gaussian = cv2.GaussianBlur(image, (0, 0), 1.0)
        sharpened = cv2.addWeighted(image, 1.15, gaussian, -0.15, 0)
        return sharpened

    def process(self, input_path: str, output_path: str) -> PreprocessingResult:
        """Executes full pipeline and saves the preprocessed image."""
        img = cv2.imread(str(input_path))
        if img is None:
            raise ValueError(f"Unable to read image at {input_path}")

        orig_h, orig_w = img.shape[:2]

        # 1. Glare reduction & contrast normalization
        enhanced = self.reduce_glare_and_enhance_contrast(img)

        # 2. Auto-deskew
        deskewed, angle = self.auto_deskew(enhanced)

        # 3. Denoising & edge sharpening
        final_img = self.denoise_and_sharpen(deskewed)

        # Save preprocessed image
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        ext = Path(output_path).suffix.lower()
        if ext in (".jpg", ".jpeg"):
            cv2.imwrite(str(output_path), final_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            cv2.imwrite(str(output_path), final_img)

        final_h, final_w = final_img.shape[:2]

        return PreprocessingResult(
            preprocessed_path=str(output_path),
            deskew_angle=round(angle, 2),
            original_dimensions=(orig_w, orig_h),
            preprocessed_dimensions=(final_w, final_h),
            metadata={
                "glare_reduction": "CLAHE (LAB)",
                "denoise": "Subtle stroke preservation",
                "sharpening": "Unsharp Mask",
                "deskew_angle_deg": round(angle, 2)
            }
        )
