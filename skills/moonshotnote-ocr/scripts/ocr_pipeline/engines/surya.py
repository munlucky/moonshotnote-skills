from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ocr_pipeline.models import OcrItem, OcrResult, safe_float, with_reading_order
from ocr_pipeline.utils import collect_text, resolve_cli, run_command


def surya_available() -> bool:
    return bool(resolve_cli("surya_ocr") or resolve_cli("surya"))


def run_surya(input_path: Path, out_dir: Path) -> OcrResult:
    candidates = []
    surya_ocr = resolve_cli("surya_ocr")
    surya = resolve_cli("surya")
    if surya_ocr:
        candidates.append([surya_ocr, str(input_path), "--output_dir", str(out_dir)])
    if surya:
        candidates.append([surya, str(input_path), "--output_dir", str(out_dir)])

    if not candidates:
        raise RuntimeError("Surya CLI was not found. Run scripts/setup.ps1 and retry.")

    attempts = []
    for command in candidates:
        result = run_command(command)
        attempts.append(result)
        if result["returncode"] == 0:
            items = find_surya_items(out_dir)
            if not items:
                text = result["stdout"].strip() or find_surya_text(out_dir)
                items = [build_item(text or "[unclear]")]
            return OcrResult(
                engine="surya",
                input_path=input_path,
                items=with_reading_order(items),
                raw={"attempts": attempts},
                warnings=["Surya CLI output shape can vary by version; inspect JSON output for details."],
                runtime_metadata={
                    "pipeline": "surya",
                    "capabilities": {"surya": {"available": True}},
                },
            )

    raise RuntimeError(json.dumps({"surya_attempts": attempts}, ensure_ascii=False, indent=2))


def find_surya_text(out_dir: Path) -> str:
    collected = []
    for path in sorted(out_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        collected.extend(collect_text(data))
    return "\n".join(line for line in collected if line)


def find_surya_items(out_dir: Path) -> list[OcrItem]:
    for path in sorted(out_dir.rglob("results.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = extract_surya_items(data)
        if items:
            return items
    return []


def extract_surya_items(value: Any) -> list[OcrItem]:
    pages = []
    if isinstance(value, dict):
        for document_pages in value.values():
            if isinstance(document_pages, list):
                pages.extend(document_pages)
    elif isinstance(value, list):
        pages = value

    items: list[OcrItem] = []
    for page_index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            continue
        for line_index, line in enumerate(page.get("text_lines", []), start=1):
            if not isinstance(line, dict):
                continue
            text = line.get("text")
            if not text:
                continue
            items.append(
                OcrItem(
                    text=str(text),
                    confidence=safe_float(line.get("confidence")),
                    box=line.get("bbox") or line.get("polygon"),
                    raw=line,
                    source_engine="surya",
                    source_block_type="text_line",
                    source_span={"page": page_index, "block_id": None, "line_id": str(line_index)},
                )
            )
    return with_reading_order(items)


def build_item(text: str) -> OcrItem:
    return OcrItem(
        text=text,
        source_engine="surya",
        source_block_type="text",
        source_span={"page": 1, "block_id": None, "line_id": None},
    )

