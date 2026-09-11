import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PIL import Image
import pytesseract
from pytesseract import Output

from config import (
    TESSERACT_CMD,
    TESSERACT_OEM,
    TESSERACT_PSM_PRIMARY,
    TESSERACT_PSM_SPARSE,
    TESSERACT_EXTRA_CONFIG,
    OCR_CONFIDENCE_THRESHOLD,
    LOW_QUALITY_THRESHOLD,
)
from .base import BaseOCREngine, OCRResult, OCRBlock, OCRLine, OCRWord, BoundingBox

logger = logging.getLogger("labelcheck.ocr")
logging.basicConfig(level=logging.INFO)


class TesseractOCREngine(BaseOCREngine):
    """
    Optimized Tesseract OCR engine with:
    - Explicit OEM 1 (LSTM-only) and configurable PSM
    - Single consolidated primary pass for high speed (< 1s)
    - Detailed raw text & word-confidence logging
    - Adaptive multi-pass retry on low confidence / sparse output
    - Low-quality photo detection and warning flag
    """

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        oem: Optional[int] = None,
        primary_psm: Optional[int] = None,
        sparse_psm: Optional[int] = None,
    ):
        cmd = tesseract_cmd or TESSERACT_CMD
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        self.oem = oem if oem is not None else TESSERACT_OEM
        self.primary_psm = primary_psm if primary_psm is not None else TESSERACT_PSM_PRIMARY
        self.sparse_psm = sparse_psm if sparse_psm is not None else TESSERACT_PSM_SPARSE

    def _run_pass(
        self, img: Image.Image, config_str: str
    ) -> Tuple[List[OCRLine], List[OCRWord], List[OCRBlock], float]:
        """Runs a single Tesseract image_to_data extraction with structured lines and words."""
        img_w, img_h = img.size
        kw = {
            "output_type": Output.DICT,
            "config": config_str,
        }

        try:
            data = pytesseract.image_to_data(img, **kw)
        except Exception as e:
            logger.error(f"Tesseract OCR pass failed: {e}")
            return [], [], [], 0.0

        words: List[OCRWord] = []
        lines_dict: Dict[tuple, List[OCRWord]] = {}
        blocks_dict: Dict[int, List[tuple]] = {}

        n_boxes = len(data.get("text", []))
        for i in range(n_boxes):
            text = str(data["text"][i]).strip()
            conf_val = float(data["conf"][i])

            if not text or conf_val < 0:
                continue

            box = BoundingBox(
                x=int(data["left"][i]),
                y=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
                image_width=img_w,
                image_height=img_h,
            )

            word_obj = OCRWord(text=text, confidence=conf_val, box=box)
            words.append(word_obj)

            b_num = data["block_num"][i]
            p_num = data["par_num"][i]
            l_num = data["line_num"][i]
            line_key = (b_num, p_num, l_num)

            if line_key not in lines_dict:
                lines_dict[line_key] = []
            lines_dict[line_key].append(word_obj)

            if b_num not in blocks_dict:
                blocks_dict[b_num] = []
            if line_key not in blocks_dict[b_num]:
                blocks_dict[b_num].append(line_key)

        ocr_lines: List[OCRLine] = []
        line_obj_map: Dict[tuple, OCRLine] = {}

        for line_key, line_words in lines_dict.items():
            line_text = " ".join(w.text for w in line_words)
            line_conf = sum(w.confidence for w in line_words) / len(line_words)
            line_box = BoundingBox.merge([w.box for w in line_words], img_w, img_h)
            if line_box:
                line_obj = OCRLine(
                    text=line_text,
                    confidence=round(line_conf, 1),
                    box=line_box,
                    words=line_words,
                )
                ocr_lines.append(line_obj)
                line_obj_map[line_key] = line_obj

        ocr_blocks: List[OCRBlock] = []
        for b_num, line_keys in blocks_dict.items():
            b_lines = [line_obj_map[k] for k in line_keys if k in line_obj_map]
            if not b_lines:
                continue
            b_text = "\n".join(l.text for l in b_lines)
            b_conf = sum(l.confidence for l in b_lines) / len(b_lines)
            b_box = BoundingBox.merge([l.box for l in b_lines], img_w, img_h)
            if b_box:
                ocr_blocks.append(
                    OCRBlock(
                        text=b_text,
                        confidence=round(b_conf, 1),
                        box=b_box,
                        lines=b_lines,
                    )
                )

        avg_conf = (sum(w.confidence for w in words) / len(words)) if words else 0.0
        return ocr_lines, words, ocr_blocks, avg_conf

    def extract(
        self,
        image_path: str,
        raw_image_path: Optional[str] = None,
        binarized_path: Optional[str] = None,
        grayscale_path: Optional[str] = None,
    ) -> OCRResult:
        """
        Executes fast single-pass OCR on binarized image.
        If confidence is below threshold, adaptively retries with alternative preprocessing
        (grayscale/adaptive) or sparse PSM, selecting the highest-scoring result.
        """
        t0 = time.perf_counter()

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Auto-discover companion binarized / grayscale files if not explicitly provided
        base_path = Path(image_path)
        if not binarized_path:
            cand_bin = base_path.parent / f"{base_path.stem}_binarized.png"
            if cand_bin.exists():
                binarized_path = str(cand_bin)
        if not grayscale_path:
            cand_gray = base_path.parent / f"{base_path.stem}_grayscale.png"
            if cand_gray.exists():
                grayscale_path = str(cand_gray)

        # Primary pass image target: prefer clean contrast-enhanced grayscale, fallback to binarized or original
        # Tesseract 5 LSTM performs best on continuous 8-bit grayscale rather than 1-bit thresholded bitmaps
        primary_target_path = (
            grayscale_path
            if (grayscale_path and os.path.exists(grayscale_path))
            else (binarized_path if (binarized_path and os.path.exists(binarized_path)) else image_path)
        )
        primary_img = Image.open(primary_target_path)
        img_w, img_h = primary_img.size

        # Primary pass config with DAWG hallucination suppression
        extra = f" {TESSERACT_EXTRA_CONFIG}".strip() if TESSERACT_EXTRA_CONFIG else ""
        primary_cfg = f"--oem {self.oem} --psm {self.primary_psm} {extra}".strip()
        logger.info(f"Running primary OCR pass on [{Path(primary_target_path).name}] with config '{primary_cfg}'")

        lines, words, blocks, avg_conf = self._run_pass(primary_img, primary_cfg)
        pass_used = f"primary (target={Path(primary_target_path).name}, psm={self.primary_psm})"

        # Log raw Tesseract output & word confidence statistics
        raw_text_preview = "\n".join(l.text for l in lines)
        logger.info(
            f"Primary OCR output: {len(words)} words, {len(lines)} lines, avg conf: {avg_conf:.1f}%. "
            f"Elapsed: {((time.perf_counter() - t0) * 1000):.1f}ms"
        )
        if words:
            conf_min = min(w.confidence for w in words)
            conf_max = max(w.confidence for w in words)
            logger.debug(f"Word confidence range: min={conf_min:.1f}%, max={conf_max:.1f}%")
            logger.debug(f"Raw OCR text preview:\n{raw_text_preview[:400]}")

        # Adaptive Retry: If confidence is low or very few words detected, retry with fallback variant
        needs_retry = (avg_conf < OCR_CONFIDENCE_THRESHOLD) or (len(words) < 6)
        if needs_retry:
            logger.info(
                f"OCR confidence ({avg_conf:.1f}%) or word count ({len(words)}) below threshold "
                f"({OCR_CONFIDENCE_THRESHOLD}%). Initiating adaptive retry pass..."
            )

            candidates: List[Tuple[Image.Image, str, str]] = []

            # Candidate A: Binarized (Otsu) with primary PSM
            if binarized_path and os.path.exists(binarized_path) and binarized_path != primary_target_path:
                candidates.append((Image.open(binarized_path), primary_cfg, f"binarized (psm={self.primary_psm})"))

            # Candidate B: Primary image with sparse text PSM (PSM 11)
            sparse_cfg = f"--oem {self.oem} --psm {self.sparse_psm} {extra}".strip()
            candidates.append((primary_img, sparse_cfg, f"sparse (psm={self.sparse_psm})"))

            # Candidate C: Adaptive binarized if exists (useful for shadows/glare)
            adaptive_cand = base_path.parent / f"{base_path.stem}_adaptive.png"
            if adaptive_cand.exists():
                candidates.append((Image.open(str(adaptive_cand)), primary_cfg, "adaptive_binarized"))

            # Evaluate retry candidates
            best_lines, best_words, best_blocks, best_conf, best_pass = lines, words, blocks, avg_conf, pass_used

            for cand_img, cand_cfg, cand_label in candidates:
                c_lines, c_words, c_blocks, c_conf = self._run_pass(cand_img, cand_cfg)
                logger.info(f"Retry candidate '{cand_label}': {len(c_words)} words, avg conf: {c_conf:.1f}%")

                # Prefer higher confidence or substantially more detected words
                is_better = (
                    (c_conf > best_conf + 3.0 and len(c_words) >= 4)
                    or (len(c_words) > len(best_words) + 5 and c_conf >= best_conf - 5.0)
                    or (len(best_words) < 4 and len(c_words) >= 4)
                )
                if is_better:
                    best_lines, best_words, best_blocks, best_conf, best_pass = (
                        c_lines,
                        c_words,
                        c_blocks,
                        c_conf,
                        f"retry_{cand_label}",
                    )

            lines, words, blocks, avg_conf, pass_used = best_lines, best_words, best_blocks, best_conf, best_pass
            raw_text_preview = "\n".join(l.text for l in lines)
            logger.info(f"Selected OCR outcome after retry: {pass_used} (conf: {avg_conf:.1f}%, words: {len(words)})")

        total_elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        # Quality warning determination
        low_quality = (avg_conf < LOW_QUALITY_THRESHOLD) or (len(words) < 4)
        quality_msg = (
            "Low image quality — please retake photo with better lighting, focus, and alignment."
            if low_quality
            else None
        )

        return OCRResult(
            raw_text=raw_text_preview,
            average_confidence=round(avg_conf, 1),
            image_width=img_w,
            image_height=img_h,
            blocks=blocks,
            lines=lines,
            words=words,
            low_quality_warning=low_quality,
            quality_message=quality_msg,
            pass_used=pass_used,
        )
