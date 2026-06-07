from __future__ import annotations

from dataclasses import dataclass

from ocr_pipeline.models import OcrItem
from ocr_pipeline.utils import normalize_box


PAGE_TYPES = {"auto", "plain-text", "table", "multi-column", "layout", "unknown"}


@dataclass
class PageTypeResult:
    page_type: str
    confidence: float
    scores: dict[str, float]


def classify_page_type(items: list[OcrItem]) -> PageTypeResult:
    boxes = [box for item in items if (box := normalize_box(item.box))]
    text_items = [item for item in items if item.text]

    if not text_items or len(boxes) < 3:
        return PageTypeResult(
            page_type="unknown",
            confidence=0.0,
            scores={
                "table_score": 0.0,
                "column_score": 0.0,
                "layout_score": 0.0,
                "median_confidence": median_confidence(items),
                "text_density": float(len(text_items)),
            },
        )

    lefts = [box[0] for box in boxes]
    rights = [box[2] for box in boxes]
    tops = [box[1] for box in boxes]
    widths = [max(1.0, box[2] - box[0]) for box in boxes]
    heights = [max(1.0, box[3] - box[1]) for box in boxes]
    page_width = max(rights) - min(lefts)
    page_height = max(box[3] for box in boxes) - min(tops)

    column_clusters = cluster_positions(lefts, max(24.0, page_width * 0.12))
    row_clusters = cluster_positions(tops, max(12.0, page_height * 0.025))
    short_line_ratio = sum(1 for item in text_items if len(item.text.strip()) <= 12) / max(1, len(text_items))
    aligned_rows = len(row_clusters) / max(1, len(text_items))
    aligned_columns = len(column_clusters) / max(1, len(text_items))
    median_width = sorted(widths)[len(widths) // 2]
    median_height = sorted(heights)[len(heights) // 2]

    table_score = clamp((short_line_ratio * 0.45) + ((1.0 - aligned_rows) * 0.25) + ((1.0 - aligned_columns) * 0.30))
    column_score = clamp((min(len(column_clusters), 3) / 3.0) * 0.75 + (1.0 if len(column_clusters) in {2, 3} else 0.0) * 0.25)
    layout_score = clamp((len(column_clusters) / 5.0) * 0.35 + (short_line_ratio * 0.25) + (median_height / max(1.0, page_height) * 2.0))
    median_conf = median_confidence(items)
    density = len(text_items) / max(1.0, page_width * page_height / 10000.0)

    scores = {
        "table_score": round(table_score, 3),
        "column_score": round(column_score, 3),
        "layout_score": round(layout_score, 3),
        "median_confidence": round(median_conf, 3),
        "text_density": round(density, 3),
        "median_width": round(median_width, 3),
    }

    if table_score >= 0.68 and len(text_items) >= 6:
        return PageTypeResult("table", table_score, scores)
    if len(column_clusters) in {2, 3} and column_score >= 0.72:
        return PageTypeResult("multi-column", column_score, scores)
    if layout_score >= 0.70:
        return PageTypeResult("layout", layout_score, scores)
    return PageTypeResult("plain-text", max(0.5, 1.0 - max(table_score, column_score, layout_score)), scores)


def cluster_positions(values: list[float], tolerance: float) -> list[list[float]]:
    clusters: list[list[float]] = []
    for value in sorted(values):
        if not clusters or abs(value - average(clusters[-1])) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return clusters


def average(values: list[float]) -> float:
    return sum(values) / max(1, len(values))


def median_confidence(items: list[OcrItem]) -> float:
    values = sorted(item.confidence for item in items if item.confidence is not None)
    if not values:
        return 0.0
    return float(values[len(values) // 2])


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))

