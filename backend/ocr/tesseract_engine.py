import pytesseract
from pytesseract import Output
from PIL import Image
from typing import Dict, List, Optional
import os

from config import TESSERACT_CMD
from .base import BaseOCREngine, OCRResult, OCRBlock, OCRLine, OCRWord, BoundingBox


class TesseractOCREngine(BaseOCREngine):
    """
    Tesseract OCR implementation conforming to BaseOCREngine.
    """

    def __init__(self, tesseract_cmd: str = None):
        cmd = tesseract_cmd or TESSERACT_CMD
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

    def _run_pass(self, img: Image.Image, config: Optional[str] = None):
        img_w, img_h = img.size
        kw = {"output_type": Output.DICT}
        if config:
            kw["config"] = config

        try:
            data = pytesseract.image_to_data(img, **kw)
        except Exception:
            return [], [], []

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
                image_height=img_h
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
                    words=line_words
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
                ocr_blocks.append(OCRBlock(
                    text=b_text,
                    confidence=round(b_conf, 1),
                    box=b_box,
                    lines=b_lines
                ))

        return ocr_lines, words, ocr_blocks

    def extract(self, image_path: str, raw_image_path: Optional[str] = None) -> OCRResult:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        img = Image.open(image_path)
        img_w, img_h = img.size

        # Pass 1: Standard layout
        lines1, words1, blocks1 = self._run_pass(img)
        # Pass 2: Sparse text layout (captures standalone lines like Net Qty, MRP, Exp)
        lines2, words2, blocks2 = self._run_pass(img, config="--psm 11")

        # If raw_image_path is provided and different from image_path, also extract from raw image
        extra_lines: List[OCRLine] = []
        extra_words: List[OCRWord] = []
        if raw_image_path and os.path.exists(raw_image_path) and os.path.abspath(raw_image_path) != os.path.abspath(image_path):
            try:
                raw_img = Image.open(raw_image_path)
                r_lines1, r_words1, _ = self._run_pass(raw_img)
                r_lines2, r_words2, _ = self._run_pass(raw_img, config="--psm 11")
                extra_lines.extend(r_lines1 + r_lines2)
                extra_words.extend(r_words1 + r_words2)
            except Exception:
                pass

        # Merge lines: preserve all lines1, add novel lines from lines2 and extra_lines
        merged_lines: List[OCRLine] = list(lines1)
        for l in (lines2 + extra_lines):
            t = l.text.strip()
            if not t:
                continue
            already_present = any(
                (len(t) > 3 and t.lower() in ml.text.lower()) or (t.lower() == ml.text.lower())
                for ml in merged_lines
            )
            if not already_present:
                merged_lines.append(l)

        # Merge words
        merged_words: List[OCRWord] = list(words1)
        for w in (words2 + extra_words):
            if not w.text.strip():
                continue
            matched = False
            for i, mw in enumerate(merged_words):
                ix1 = max(mw.box.x, w.box.x)
                iy1 = max(mw.box.y, w.box.y)
                ix2 = min(mw.box.x + mw.box.width, w.box.x + w.box.width)
                iy2 = min(mw.box.y + mw.box.height, w.box.y + w.box.height)
                if ix2 > ix1 and iy2 > iy1:
                    inter_area = (ix2 - ix1) * (iy2 - iy1)
                    w_area = w.box.width * w.box.height
                    if w_area > 0 and (inter_area / w_area) > 0.35:
                        matched = True
                        if w.confidence > (mw.confidence + 15):
                            merged_words[i] = w
                        break
            if not matched:
                merged_words.append(w)

        all_text = "\n".join(l.text for l in merged_lines)
        avg_conf = (sum(w.confidence for w in merged_words) / len(merged_words)) if merged_words else 0.0

        return OCRResult(
            raw_text=all_text,
            average_confidence=round(avg_conf, 1),
            image_width=img_w,
            image_height=img_h,
            blocks=blocks1 + [b for b in blocks2 if b.text not in [b1.text for b1 in blocks1]],
            lines=merged_lines,
            words=merged_words
        )
