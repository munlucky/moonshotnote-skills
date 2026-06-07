from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LOW_CONFIDENCE_THRESHOLD = 0.75


@dataclass
class OcrItem:
    text: str
    confidence: float | None = None
    box: Any | None = None
    raw: Any | None = None
    source_engine: str | None = None
    source_block_type: str | None = None
    source_span: dict[str, Any] | None = None
    reading_order: int | None = None


@dataclass
class OcrResult:
    engine: str
    input_path: Path
    items: list[OcrItem]
    raw: Any | None = None
    warnings: list[str] = field(default_factory=list)
    requested_engine: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    page_type: str = "unknown"
    page_type_confidence: float = 0.0
    page_type_scores: dict[str, float] = field(default_factory=dict)
    runtime_metadata: dict[str, Any] = field(default_factory=dict)
    structured: dict[str, Any] = field(
        default_factory=lambda: {
            "tables": [],
            "columns": [],
            "layout_blocks": [],
            "markdown": None,
        }
    )

    @property
    def text(self) -> str:
        lines = []
        for item in self.items:
            if not item.text:
                continue
            if item.confidence is not None and item.confidence < LOW_CONFIDENCE_THRESHOLD:
                lines.append("[unclear]")
            else:
                lines.append(item.text)
        return "\n".join(lines)


@dataclass
class PaddleRunner:
    ocr: Any
    mode: str
    warnings: list[str]


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def with_reading_order(items: list[OcrItem]) -> list[OcrItem]:
    for index, item in enumerate(items, start=1):
        if item.reading_order is None:
            item.reading_order = index
    return items

