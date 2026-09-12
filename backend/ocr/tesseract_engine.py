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
    MAX_IMAGE_DIMENSION,
    OCR_SLOW_THRESHOLD_SEC,
    OCR_PER_PASS_TIMEOUT_SEC,
)
from .base import BaseOCREngine, OCRResult, OCRBlock, OCRLine, OCRWord, BoundingBox

logger = logging.getLogger("labelcheck.ocr")
logging.basicConfig(level=logging.INFO)


class TesseractOCREngine(BaseOCREngine):
    """
    Optimized Tesseract OCR engine with:
    - Hard dimension cap at 1200px before OCR to protect constrained vCPUs
    - Explicit OEM 1 (LSTM-only) and configurable PSM
    - Strictly at most 1 second OCR pass only if conf < threshold AND words < 3
    - 10-second slow OCR logging for cloud diagnostics
    - Distinct error state for timeouts vs empty text
    """

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        oem: Optional[int] = None,
        primary_psm: Optional[int] = None,
        sparse_psm: Optional[int] = None,
        max_dimension: Optional[int] = None,
    ):
        cmd = tesseract_cmd or TESSERACT_CMD
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        self.oem = oem if oem is not None else TESSERACT_OEM
        self.primary_psm = primary_psm if primary_psm is not None else TESSERACT_PSM_PRIMARY
        self.sparse_psm = sparse_psm if sparse_psm is not None else TESSERACT_PSM_SPARSE
        self.max_dimension = max_dimension or MAX_IMAGE_DIMENSION

    def _enforce_max_dimension(self, img: Image.Image) -> Tuple[Image.Image, int, int]:
        """Strictly caps image dimensions to max_dimension (1200px) on longest side."""
        w, h = img.size
        longest = max(w, h)
        if longest > self.max_dimension:
            scale = self.max_dimension / float(longest)
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
            logger.info(
                f"Hard-capped OCR image dimension from ({w}, {h}) to ({new_w}, {new_h}) [cap: {self.max_dimension}px]"
            )
            return img, new_w, new_h
        return img, w, h

    def _run_pass(
        self, img: Image.Image, config_str: str, timeout_sec: Optional[int] = None
    ) -> Tuple[List[OCRLine], List[OCRWord], List[OCRBlock], float]:
        """Runs a single Tesseract image_to_data extraction with structured lines and words."""
        img, img_w, img_h = self._enforce_max_dimension(img)
        pass_timeout = timeout_sec or OCR_PER_PASS_TIMEOUT_SEC
        kw = {
            "output_type": Output.DICT,
            "config": config_str,
            "timeout": pass_timeout,
        }

        try:
            data = pytesseract.image_to_data(img, **kw)
        except pytesseract.pytesseract.TesseractTimeoutError as te:
            logger.error(f"Tesseract OCR pass timed out after {pass_timeout}s: {te}")
            raise TimeoutError(f"Tesseract OCR pass timed out after {pass_timeout}s") from te
        except Exception as e:
            if "timeout" in str(e).lower():
                logger.error(f"Tesseract OCR pass timed out: {e}")
                raise TimeoutError("Tesseract OCR pass timed out") from e
            logger.error(f"Tesseract OCR pass failed: {e}")
            raise e

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

        # Primary pass image target: prefer preprocessed image (contrast balanced, deskewed, sharpened)
        # Fallback to grayscale, binarized, or raw image if needed
        primary_target_path = (
            image_path
            if (image_path and os.path.exists(image_path))
            else (grayscale_path if (grayscale_path and os.path.exists(grayscale_path)) else (binarized_path or image_path))
        )
        primary_img = Image.open(primary_target_path)
        primary_img, img_w, img_h = self._enforce_max_dimension(primary_img)

        # Primary pass config with DAWG hallucination suppression
        extra = f" {TESSERACT_EXTRA_CONFIG}".strip() if TESSERACT_EXTRA_CONFIG else ""
        primary_cfg = f"--oem {self.oem} --psm {self.primary_psm} {extra}".strip()
        logger.info(
            f"Running primary OCR pass on [{Path(primary_target_path).name}] ({img_w}x{img_h}) with config '{primary_cfg}'"
        )

        try:
            lines, words, blocks, avg_conf = self._run_pass(primary_img, primary_cfg)
            pass_used = f"primary (target={Path(primary_target_path).name}, psm={self.primary_psm})"

            # Log raw Tesseract output & word confidence statistics
            raw_text_preview = "\n".join(l.text for l in lines)
            logger.info(
                f"Primary OCR output: {len(words)} words, {len(lines)} lines, avg conf: {avg_conf:.1f}%. "
                f"Elapsed: {((time.perf_counter() - t0) * 1000):.1f}ms"
            )

            # Fast Early-Exit on total illegibility / zero words
            if avg_conf < 10.0 and len(words) == 0:
                logger.info("Primary OCR produced 0 words and <10% confidence. Attempting single binarized fallback.")
                if binarized_path and os.path.exists(binarized_path) and binarized_path != primary_target_path:
                    bin_img = Image.open(binarized_path)
                    bin_img, _, _ = self._enforce_max_dimension(bin_img)
                    c_lines, c_words, c_blocks, c_conf = self._run_pass(bin_img, primary_cfg)
                    if len(c_words) > 0:
                        lines, words, blocks, avg_conf = c_lines, c_words, c_blocks, c_conf
                        pass_used = f"early_exit_binarized (target={Path(binarized_path).name})"
                        raw_text_preview = "\n".join(l.text for l in lines)
                    else:
                        logger.info("Binarized fallback also returned 0 words. Exiting OCR early.")

            # Item 1: ONLY attempt a second OCR pass if confidence is below threshold AND words < 3
            # Strictly at most 1 second pass — never run all 4 variants
            needs_second_pass = (avg_conf < OCR_CONFIDENCE_THRESHOLD) and (len(words) < 3)

            if needs_second_pass:
                logger.info(
                    f"Triggering second OCR pass: confidence ({avg_conf:.1f}% < {OCR_CONFIDENCE_THRESHOLD}%) "
                    f"AND word count ({len(words)} < 3)..."
                )

                # Pick the single best alternative variant for the second pass
                second_target_path = None
                if binarized_path and os.path.exists(binarized_path) and binarized_path != primary_target_path:
                    second_target_path = binarized_path
                elif grayscale_path and os.path.exists(grayscale_path) and grayscale_path != primary_target_path:
                    second_target_path = grayscale_path
                else:
                    cand_adap = base_path.parent / f"{base_path.stem}_adaptive.png"
                    if cand_adap.exists():
                        second_target_path = str(cand_adap)

                if second_target_path:
                    sec_img = Image.open(second_target_path)
                    sec_img, _, _ = self._enforce_max_dimension(sec_img)
                    logger.info(f"Running second (and final) OCR pass on [{Path(second_target_path).name}]")
                    c_lines, c_words, c_blocks, c_conf = self._run_pass(sec_img, primary_cfg)
                    logger.info(f"Second OCR pass result: {len(c_words)} words, avg conf: {c_conf:.1f}%")

                    # Adopt second pass only if it genuinely improved over the first pass
                    if len(c_words) > len(words) or (len(c_words) == len(words) and c_conf > avg_conf):
                        lines, words, blocks, avg_conf = c_lines, c_words, c_blocks, c_conf
                        pass_used = f"second_pass (target={Path(second_target_path).name})"
                        raw_text_preview = "\n".join(l.text for l in lines)
                else:
                    logger.info("No alternative image variant available for second pass. Keeping primary pass.")

        except TimeoutError as te:
            total_elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(f"[OCR TIMEOUT] OCR processing timed out after {total_elapsed_ms}ms: {te}")
            return OCRResult(
                raw_text="",
                average_confidence=0.0,
                image_width=img_w,
                image_height=img_h,
                blocks=[],
                lines=[],
                words=[],
                low_quality_warning=True,
                quality_message="Processing took too long, please try a smaller or clearer image.",
                pass_used="timeout",
                timed_out=True,
                error_message="Processing took too long, please try a smaller or clearer image.",
            )
        except Exception as e:
            total_elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(f"[OCR ERROR] OCR processing crashed after {total_elapsed_ms}ms: {e}", exc_info=True)
            return OCRResult(
                raw_text="",
                average_confidence=0.0,
                image_width=img_w,
                image_height=img_h,
                blocks=[],
                lines=[],
                words=[],
                low_quality_warning=True,
                quality_message=f"OCR processing failed: {str(e)}. Please try a different photo.",
                pass_used="error",
                timed_out=False,
                error_message=f"OCR processing failed: {str(e)}",
            )

        # Performance timing check: Item 3 log clearly whenever OCR takes longer than 10 seconds
        total_elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        total_elapsed_sec = total_elapsed_ms / 1000.0
        if total_elapsed_sec > OCR_SLOW_THRESHOLD_SEC:
            logger.warning(
                f"[PERFORMANCE WARNING] OCR extraction took {total_elapsed_sec:.2f}s (> {OCR_SLOW_THRESHOLD_SEC}s threshold)! "
                f"Image: {Path(image_path).name} ({img_w}x{img_h}), Pass: '{pass_used}', Words: {len(words)}"
            )
        else:
            logger.info(f"OCR extraction completed in {total_elapsed_sec:.2f}s ({total_elapsed_ms}ms)")

        # Low-quality determination
        low_quality = (avg_conf < LOW_QUALITY_THRESHOLD) or (len(words) < 3)
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
            timed_out=False,
            error_message=None,
        )
