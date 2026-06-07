from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from ocr_pipeline.models import OcrItem, OcrResult, safe_float, with_reading_order
from ocr_pipeline.utils import collect_text


def probe_pp_structure() -> dict[str, Any]:
    try:
        module = importlib.import_module("paddleocr")
    except Exception as exc:
        return {"available": False, "reason": f"paddleocr import failed: {exc}"}

    if not hasattr(module, "PPStructureV3"):
        return {"available": False, "reason": "paddleocr.PPStructureV3 is not available"}

    return {"available": True, "reason": None}


def pp_structure_available() -> bool:
    return bool(probe_pp_structure()["available"])


def create_pp_structure_runner() -> Any:
    from paddleocr import PPStructureV3

    try:
        return PPStructureV3()
    except TypeError:
        return PPStructureV3


def run_pp_structure(input_path: Path) -> OcrResult:
    probe = probe_pp_structure()
    if not probe["available"]:
        raise RuntimeError(f"PP-StructureV3 unavailable: {probe['reason']}")

    runner = create_pp_structure_runner()
    if hasattr(runner, "predict"):
        raw = runner.predict(str(input_path))
    elif callable(runner):
        raw = runner(str(input_path))
    else:
        raise RuntimeError("PP-StructureV3 runner does not expose a supported call interface")

    items = normalize_pp_structure_result(raw)
    structured = normalize_structured(raw)
    if not items:
        text = structured.get("markdown") or "\n".join(collect_text(raw)) or "[unclear]"
        items = [build_item(text, raw=raw)]

    return OcrResult(
        engine="pp-structure",
        input_path=input_path,
        items=with_reading_order(items),
        raw=raw,
        warnings=["PP-StructureV3 output shape can vary by version; inspect structured JSON for details."],
        runtime_metadata={
            "pipeline": "pp-structure",
            "capabilities": {"pp_structure": probe},
        },
        structured=structured,
    )


def normalize_pp_structure_result(raw: Any) -> list[OcrItem]:
    items: list[OcrItem] = []

    for page_index, page in enumerate(as_pages(raw), start=1):
        if hasattr(page, "json"):
            page = page.json
        if isinstance(page, dict):
            overall = page.get("overall_ocr_res")
            if isinstance(overall, dict):
                items.extend(extract_ocr_mapping(overall, page_index))
            for block_index, block in enumerate(page.get("parsing_res_list") or [], start=1):
                if not isinstance(block, dict):
                    continue
                text = block.get("block_content") or block.get("text")
                if text:
                    items.append(
                        build_item(
                            str(text),
                            confidence=safe_float(block.get("confidence")),
                            box=block.get("block_bbox") or block.get("bbox"),
                            page_index=page_index,
                            block_id=str(block_index),
                            block_type=str(block.get("block_label") or block.get("sub_label") or "layout_block"),
                            raw=block,
                        )
                    )
        elif isinstance(page, str):
            items.append(build_item(page, page_index=page_index, raw=page))

    return with_reading_order(items)


def normalize_structured(raw: Any) -> dict[str, Any]:
    structured = {"tables": [], "columns": [], "layout_blocks": [], "markdown": None}

    for page in as_pages(raw):
        if hasattr(page, "json"):
            page = page.json
        if not isinstance(page, dict):
            continue
        for key in ("markdown", "md"):
            if isinstance(page.get(key), str) and not structured["markdown"]:
                structured["markdown"] = page[key]
        for block in page.get("parsing_res_list") or []:
            if not isinstance(block, dict):
                continue
            label = str(block.get("block_label") or block.get("sub_label") or "")
            entry = {
                "label": label,
                "bbox": block.get("block_bbox") or block.get("bbox"),
                "content": block.get("block_content") or block.get("text") or "",
            }
            structured["layout_blocks"].append(entry)
            if "table" in label.lower():
                structured["tables"].append(entry)

    return structured


def extract_ocr_mapping(data: dict[str, Any], page_index: int) -> list[OcrItem]:
    texts = data.get("rec_texts") or data.get("texts") or data.get("text")
    scores = data.get("rec_scores") or data.get("scores") or data.get("confidence")
    boxes = data.get("rec_boxes") or data.get("dt_polys") or data.get("boxes")
    if isinstance(texts, str):
        return [build_item(texts, confidence=safe_float(scores), box=boxes, page_index=page_index, raw=data)]
    if not isinstance(texts, list):
        return []
    items = []
    for index, text in enumerate(texts):
        confidence = scores[index] if isinstance(scores, list) and index < len(scores) else None
        box = boxes[index] if isinstance(boxes, list) and index < len(boxes) else None
        items.append(build_item(str(text), confidence=safe_float(confidence), box=box, page_index=page_index, line_id=str(index + 1)))
    return items


def as_pages(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    return [raw]


def build_item(
    text: str,
    *,
    confidence: float | None = None,
    box: Any | None = None,
    page_index: int = 1,
    block_id: str | None = None,
    line_id: str | None = None,
    block_type: str = "layout_block",
    raw: Any | None = None,
) -> OcrItem:
    return OcrItem(
        text=text,
        confidence=confidence,
        box=box,
        raw=raw,
        source_engine="pp-structure",
        source_block_type=block_type,
        source_span={"page": page_index, "block_id": block_id, "line_id": line_id},
    )

