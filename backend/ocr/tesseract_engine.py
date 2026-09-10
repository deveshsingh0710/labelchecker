import pytesseract
from pytesseract import Output
from PIL import Image
from typing import Dict, List
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

    def extract(self, image_path: str) -> OCRResult:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        img = Image.open(image_path)
        img_w, img_h = img.size

        # Run Tesseract with word and block level bounding boxes
        data = pytesseract.image_to_data(
            img,
            output_type=Output.DICT
        )

        words: List[OCRWord] = []
        lines_dict: Dict[int, List[OCRWord]] = {}
        blocks_dict: Dict[int, List[int]] = {}  # block_num -> list of line_keys

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf_val = float(data["conf"][i])

            # Ignore empty tokens and negative confidence
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

            # Unique key per line: (block_num, par_num, line_num)
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

        # Assemble lines
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

        # Assemble blocks
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

        all_text = "\n".join(l.text for l in ocr_lines)
        avg_conf = (sum(w.confidence for w in words) / len(words)) if words else 0.0

        return OCRResult(
            raw_text=all_text,
            average_confidence=round(avg_conf, 1),
            image_width=img_w,
            image_height=img_h,
            blocks=ocr_blocks,
            lines=ocr_lines,
            words=words
        )
