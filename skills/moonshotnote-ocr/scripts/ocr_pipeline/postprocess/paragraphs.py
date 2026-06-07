from __future__ import annotations

from ocr_pipeline.models import OcrItem
from ocr_pipeline.utils import normalize_box


def restore_paragraphs(items: list[OcrItem]) -> list[str]:
    positioned = []
    for item in items:
        box = normalize_box(item.box)
        if box:
            positioned.append((box[1], box[0], item.text))
    if not positioned:
        return [item.text for item in items if item.text]

    positioned.sort()
    lines = [text for _, _, text in positioned if text]
    return merge_short_lines(lines)


def merge_short_lines(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        current.append(stripped)
        if stripped.endswith((".", "!", "?", "다", "요", "음", "함", "임")):
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs

