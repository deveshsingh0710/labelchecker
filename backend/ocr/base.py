from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    image_width: int
    image_height: int

    @property
    def x_max(self) -> int:
        return self.x + self.width

    @property
    def y_max(self) -> int:
        return self.y + self.height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "image_width": self.image_width,
            "image_height": self.image_height,
            # Normalized percentage (0 to 100%) for responsive frontend scaling
            "normalized": {
                "top": round((self.y / max(self.image_height, 1)) * 100, 2),
                "left": round((self.x / max(self.image_width, 1)) * 100, 2),
                "width": round((self.width / max(self.image_width, 1)) * 100, 2),
                "height": round((self.height / max(self.image_height, 1)) * 100, 2),
            }
        }

    @classmethod
    def merge(cls, boxes: List["BoundingBox"], img_w: int, img_h: int) -> Optional["BoundingBox"]:
        if not boxes:
            return None
        min_x = min(b.x for b in boxes)
        min_y = min(b.y for b in boxes)
        max_x = max(b.x + b.width for b in boxes)
        max_y = max(b.y + b.height for b in boxes)
        return cls(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            image_width=img_w,
            image_height=img_h
        )


@dataclass
class OCRWord:
    text: str
    confidence: float
    box: BoundingBox


@dataclass
class OCRLine:
    text: str
    confidence: float
    box: BoundingBox
    words: List[OCRWord] = field(default_factory=list)


@dataclass
class OCRBlock:
    text: str
    confidence: float
    box: BoundingBox
    lines: List[OCRLine] = field(default_factory=list)


@dataclass
class OCRResult:
    raw_text: str
    average_confidence: float
    image_width: int
    image_height: int
    blocks: List[OCRBlock] = field(default_factory=list)
    lines: List[OCRLine] = field(default_factory=list)
    words: List[OCRWord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "average_confidence": round(self.average_confidence, 1),
            "image_width": self.image_width,
            "image_height": self.image_height,
            "total_lines": len(self.lines),
            "total_words": len(self.words),
        }


class BaseOCREngine(ABC):
    """
    Abstract interface for OCR engines.
    Allows seamlessly swapping Tesseract with Google Cloud Vision, AWS Textract, etc.
    """

    @abstractmethod
    def extract(self, image_path: str, raw_image_path: Optional[str] = None) -> OCRResult:
        """Extract text, confidence scores, and bounding boxes from an image."""
        pass
