from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from ocr_pipeline.models import LOW_CONFIDENCE_THRESHOLD, OcrItem, OcrResult


def low_confidence_items(items: list[OcrItem]) -> list[str]:
    suspicious = []
    for item in items:
        if item.confidence is not None and item.confidence < LOW_CONFIDENCE_THRESHOLD:
            suspicious.append(item.text or "[unclear]")
    return suspicious


def write_outputs(result: OcrResult, out_dir: Path, args: Namespace) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = result.input_path.stem
    prefix = f"{stem}.{result.engine}"
    txt_path = out_dir / f"{prefix}.txt"
    json_path = out_dir / f"{prefix}.json"
    md_path = out_dir / f"{prefix}.md"

    text = result.text
    if not text.strip():
        text = "[unclear]"

    payload = result_payload(result, text)
    txt_path.write_text(text + "\n", encoding="utf-8")
    written = {"txt": txt_path}
    if args.json or args.all:
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        written["json"] = json_path
    if args.md or args.all:
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        written["md"] = md_path
    return written


def result_payload(result: OcrResult, text: str | None = None) -> dict[str, Any]:
    low_confidence = low_confidence_items(result.items)
    return {
        "engine": result.engine,
        "requested_engine": result.requested_engine or result.engine,
        "fallback_used": result.fallback_used,
        "fallback_reason": result.fallback_reason,
        "page_type": result.page_type,
        "page_type_confidence": result.page_type_confidence,
        "page_type_scores": result.page_type_scores,
        "runtime_metadata": result.runtime_metadata,
        "structured": result.structured,
        "input": str(result.input_path),
        "text": text if text is not None else result.text,
        "items": [
            {
                "text": item.text,
                "confidence": item.confidence,
                "box": item.box,
                "raw": item.raw,
                "source_engine": item.source_engine,
                "source_block_type": item.source_block_type,
                "source_span": item.source_span,
                "reading_order": item.reading_order,
            }
            for item in result.items
        ],
        "warnings": result.warnings or [],
        "low_confidence": low_confidence,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    low_confidence = payload["low_confidence"]
    warnings = payload["warnings"]
    parts = [
        f"# OCR Result: {Path(payload['input']).name}",
        "",
        f"- Engine: {payload['engine']}",
        f"- Requested engine: {payload.get('requested_engine', payload['engine'])}",
        f"- Page type: {payload.get('page_type', 'unknown')} ({payload.get('page_type_confidence', 0):.3f})",
        f"- Input: `{payload['input']}`",
    ]
    if payload.get("fallback_used"):
        parts.append("- Fallback: " + str(payload.get("fallback_reason") or "used"))
    if warnings:
        parts.append("- Warnings: " + "; ".join(warnings))
    if low_confidence:
        parts.append("- Low-confidence lines: " + str(len(low_confidence)))
    parts.extend(["", "## Text", "", "```text", payload["text"], "```", ""])
    if low_confidence:
        parts.extend(["## Low-confidence", ""])
        parts.extend(f"- {line}" for line in low_confidence)
        parts.append("")
    return "\n".join(parts)

