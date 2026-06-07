from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ocr_pipeline.models import OcrItem, OcrResult, PaddleRunner, safe_float, with_reading_order


def create_paddle_runner(lang: str) -> PaddleRunner:
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    from paddleocr import PaddleOCR

    warnings: list[str] = []
    try:
        ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
        )
        return PaddleRunner(ocr=ocr, mode="predict", warnings=warnings)
    except TypeError:
        warnings.append("Used PaddleOCR legacy initialization fallback.")
        ocr = PaddleOCR(lang=lang, use_angle_cls=True)
        return PaddleRunner(ocr=ocr, mode="ocr", warnings=warnings)


def run_paddle(input_path: Path, lang: str, runner: PaddleRunner | None = None) -> OcrResult:
    runner = runner or create_paddle_runner(lang)
    if runner.mode == "predict":
        result = runner.ocr.predict(str(input_path))
    else:
        result = runner.ocr.ocr(str(input_path), cls=True)

    return OcrResult(
        engine="paddle",
        input_path=input_path,
        items=normalize_paddle_result(result),
        raw=result,
        warnings=list(runner.warnings),
        runtime_metadata={
            "pipeline": "paddle",
            "model_settings": {"lang": lang, "runner_mode": runner.mode},
            "capabilities": {"paddle": {"available": True}},
        },
    )


def normalize_paddle_result(result: Any) -> list[OcrItem]:
    items: list[OcrItem] = []

    for page_index, page in enumerate(result or [], start=1):
        if hasattr(page, "json"):
            data = page.json
            extracted = extract_from_mapping(data, page_index)
            if extracted:
                items.extend(extracted)
            else:
                items.append(build_item(str(data), page_index=page_index, raw=data))
            continue

        if isinstance(page, dict):
            extracted = extract_from_mapping(page, page_index)
            if extracted:
                items.extend(extracted)
            else:
                items.append(build_item(json.dumps(page, ensure_ascii=False), page_index=page_index, raw=page))
            continue

        if isinstance(page, list):
            for entry in page:
                items.append(parse_legacy_paddle_entry(entry, page_index))
            continue

        items.append(build_item(str(page), page_index=page_index, raw=page))

    return with_reading_order(items)


def extract_from_mapping(data: dict[str, Any], page_index: int = 1) -> list[OcrItem]:
    if isinstance(data.get("res"), dict):
        data = data["res"]

    texts = data.get("rec_texts") or data.get("texts") or data.get("text")
    scores = data.get("rec_scores") or data.get("scores") or data.get("confidence")
    boxes = data.get("rec_boxes") or data.get("dt_polys") or data.get("boxes")

    if isinstance(texts, str):
        return [build_item(texts, confidence=safe_float(scores), box=boxes, page_index=page_index, raw=data)]

    if not isinstance(texts, list):
        return []

    output = []
    for index, text in enumerate(texts):
        confidence = scores[index] if isinstance(scores, list) and index < len(scores) else None
        box = boxes[index] if isinstance(boxes, list) and index < len(boxes) else None
        output.append(
            build_item(
                str(text),
                confidence=safe_float(confidence),
                box=box,
                page_index=page_index,
                line_id=str(index + 1),
            )
        )
    return output


def parse_legacy_paddle_entry(entry: Any, page_index: int = 1) -> OcrItem:
    try:
        box = entry[0]
        text = entry[1][0]
        confidence = safe_float(entry[1][1])
        return build_item(str(text), confidence=confidence, box=box, page_index=page_index, raw=entry)
    except Exception:
        return build_item(str(entry), page_index=page_index, raw=entry)


def build_item(
    text: str,
    *,
    confidence: float | None = None,
    box: Any | None = None,
    page_index: int = 1,
    line_id: str | None = None,
    raw: Any | None = None,
) -> OcrItem:
    return OcrItem(
        text=text,
        confidence=confidence,
        box=box,
        raw=raw,
        source_engine="paddle",
        source_block_type="text_line",
        source_span={"page": page_index, "block_id": None, "line_id": line_id},
    )

