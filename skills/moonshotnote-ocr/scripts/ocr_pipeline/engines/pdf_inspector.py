from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ocr_pipeline.models import OcrItem, OcrResult, with_reading_order


def pdf_inspector_available() -> bool:
    return importlib.util.find_spec("pdf_inspector") is not None


@dataclass
class PdfInspectionInfo:
    pdf_type: str  # "text_based", "scanned", "image_based", "mixed", or "unknown"
    markdown: str | None
    confidence: float
    page_count: int
    raw: Any | None = None


def inspect_pdf(pdf_path: Path) -> PdfInspectionInfo:
    if not pdf_inspector_available():
        return fallback_inspect_pdf(pdf_path)

    try:
        import pdf_inspector
        result = pdf_inspector.process_pdf(str(pdf_path))
        pdf_type = getattr(result, "pdf_type", "unknown")
        markdown = getattr(result, "markdown", None)
        confidence = float(getattr(result, "confidence", 1.0))
        page_count = int(getattr(result, "page_count", 1))
        return PdfInspectionInfo(
            pdf_type=str(pdf_type),
            markdown=markdown,
            confidence=confidence,
            page_count=page_count,
            raw=result,
        )
    except Exception as exc:
        fallback = fallback_inspect_pdf(pdf_path)
        fallback.raw = {"error": str(exc)}
        return fallback


def fallback_inspect_pdf(pdf_path: Path) -> PdfInspectionInfo:
    if importlib.util.find_spec("pypdf") is None:
        return PdfInspectionInfo(
            pdf_type="scanned",
            markdown=None,
            confidence=0.5,
            page_count=1,
            raw={"reason": "pypdf and pdf_inspector unavailable"},
        )

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages_text = []
        has_text_pages = False
        has_empty_pages = False

        for page in reader.pages:
            t = page.extract_text() or ""
            pages_text.append(t)
            if len(t.strip()) > 20:
                has_text_pages = True
            else:
                has_empty_pages = True

        page_count = len(reader.pages)
        if has_text_pages and not has_empty_pages:
            pdf_type = "text_based"
            markdown = "\n\n".join(pages_text)
        elif has_text_pages and has_empty_pages:
            pdf_type = "mixed"
            markdown = "\n\n".join(pages_text)
        else:
            pdf_type = "scanned"
            markdown = None

        return PdfInspectionInfo(
            pdf_type=pdf_type,
            markdown=markdown,
            confidence=0.8,
            page_count=page_count,
        )
    except Exception as exc:
        return PdfInspectionInfo(
            pdf_type="scanned",
            markdown=None,
            confidence=0.0,
            page_count=1,
            raw={"error": str(exc)},
        )


def run_pdf_inspector(pdf_path: Path) -> OcrResult:
    info = inspect_pdf(pdf_path)
    items: list[OcrItem] = []

    text_content = info.markdown or ""
    if text_content.strip():
        for line in text_content.splitlines():
            line_str = line.strip()
            if line_str:
                items.append(
                    OcrItem(
                        text=line_str,
                        confidence=1.0,
                        source_engine="pdf-inspector",
                    )
                )

    page_type = (
        "plain-text"
        if info.pdf_type == "text_based"
        else ("layout" if info.pdf_type == "mixed" else "scanned")
    )

    result = OcrResult(
        engine="pdf-inspector",
        input_path=pdf_path,
        items=with_reading_order(items),
        raw=info.raw,
        page_type=page_type,
        page_type_confidence=info.confidence,
        runtime_metadata={
            "pdf_type": info.pdf_type,
            "page_count": info.page_count,
            "pdf_inspector_installed": pdf_inspector_available(),
        },
        structured={
            "tables": [],
            "columns": [],
            "layout_blocks": [],
            "markdown": info.markdown,
        },
    )

    if not items and info.pdf_type in {"scanned", "image_based"}:
        result.warnings.append("pdf-inspector classified PDF as scanned/image-based; downstream OCR required.")

    return result
