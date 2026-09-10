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
        """Detect and correct rotation skew in the label image."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Otsu thresholding after Gaussian blur to isolate text regions
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Dilate text blocks to form solid contours
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        angles = []
        h, w = image.shape[:2]
        min_area = (w * h) * 0.001  # ignore tiny noise contours

        for c in contours:
            area = cv2.contourArea(c)
            if area > min_area:
                rect = cv2.minAreaRect(c)
                angle = rect[-1]
                # In OpenCV, minAreaRect angle is in [-90, 0)
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                if -45 < angle < 45 and abs(angle) > 0.3:
                    angles.append(angle)

        if not angles:
            return image, 0.0

        # Calculate median angle
        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.4:
            return image, 0.0

        # Rotate image around center
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        deskewed = cv2.warpAffine(
            image,
            rot_mat,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return deskewed, median_angle

    def reduce_glare_and_enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast and balance illumination using CLAHE on the L channel in LAB."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
        enhanced_l = clahe.apply(l_channel)
        
        merged = cv2.merge((enhanced_l, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def denoise_and_sharpen(self, image: np.ndarray) -> np.ndarray:
        """Denoise using bilateral filter, then subtly sharpen text edges."""
        # Bilateral filter preserves sharp edges of characters
        denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Unsharp mask for crisp characters
        gaussian = cv2.GaussianBlur(denoised, (0, 0), 2.0)
        sharpened = cv2.addWeighted(denoised, 1.35, gaussian, -0.35, 0)
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
        cv2.imwrite(str(output_path), final_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

        final_h, final_w = final_img.shape[:2]

        return PreprocessingResult(
            preprocessed_path=str(output_path),
            deskew_angle=round(angle, 2),
            original_dimensions=(orig_w, orig_h),
            preprocessed_dimensions=(final_w, final_h),
            metadata={
                "glare_reduction": "CLAHE (LAB)",
                "denoise": "Bilateral Filter",
                "sharpening": "Unsharp Mask",
                "deskew_angle_deg": round(angle, 2)
            }
        )
