#!/usr/bin/env python3
"""Delegate capture OCR to ocr-document-processor and record an OCR manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_command(args: list[str], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"command": args, "returncode": None, "stdout": "", "stderr": "", "dryRun": True}
    try:
        proc = subprocess.run(args, text=True, capture_output=True, check=False)
        return {"command": args, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "dryRun": False}
    except FileNotFoundError as exc:
        return {"command": args, "returncode": 127, "stdout": "", "stderr": str(exc), "dryRun": False}


def command_ok(result: dict[str, Any]) -> bool:
    return result["returncode"] in (0, None)


def find_ocr_processor(explicit: str) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    candidates = [
        Path.home() / ".codex" / "skills" / "ocr-document-processor" / "scripts" / "ocr_processor.py",
        Path.cwd() / "ocr-document-processor" / "scripts" / "ocr_processor.py",
    ]
    for path in candidates:
        if path.exists():
            return path
    found = shutil.which("ocr_processor.py")
    return Path(found) if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OCR batch through ocr-document-processor.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", default="captures", help="Capture image directory.")
    parser.add_argument("--output", default=".", help="Run output directory.")
    parser.add_argument("--lang", default="kor+eng", help="OCR language.")
    parser.add_argument("--max-pages", type=int, default=0, help="Optional page bound recorded in manifest; 0 means all.")
    parser.add_argument("--wait-ms", type=int, default=700, help="Recorded wait time for consistency.")
    parser.add_argument("--turn-key", default="ArrowRight", help="Recorded turn key for consistency.")
    parser.add_argument("--processor", default="", help="Optional path to ocr_processor.py.")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output = Path(args.output)
    ocr_dir = output / "ocr"
    processor = find_ocr_processor(args.processor)
    warnings: list[str] = []

    if processor is None:
        warnings.append("ocr-processor-not-found")
        processor_arg = "ocr-document-processor/scripts/ocr_processor.py"
    else:
        processor_arg = str(processor)

    markdown_command = [
        "python3",
        processor_arg,
        str(input_dir),
        "--output",
        str(ocr_dir),
        "--format",
        "markdown",
        "--lang",
        args.lang,
        "--batch",
    ]
    json_dir = ocr_dir / "json"
    json_command = [
        "python3",
        processor_arg,
        str(input_dir),
        "--output",
        str(json_dir),
        "--format",
        "json",
        "--lang",
        args.lang,
        "--batch",
    ]

    if not args.dry_run:
        output.mkdir(parents=True, exist_ok=True)
        ocr_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

    markdown_result = run_command(markdown_command, args.dry_run)
    json_result = run_command(json_command, args.dry_run)
    if not command_ok(markdown_result) or not command_ok(json_result):
        warnings.append("ocr-command-failed")

    pages: list[dict[str, Any]] = []
    images = sorted(input_dir.glob("page-*.png")) if input_dir.exists() else []
    if args.max_pages:
        images = images[: args.max_pages]
    for image in images:
        stem = image.stem
        pages.append({
            "pageIndex": int(stem.split("-")[-1]) if stem.split("-")[-1].isdigit() else None,
            "imagePath": str(image),
            "ocrMarkdownPath": str(ocr_dir / f"{stem}.md"),
            "ocrJsonPath": str(json_dir / f"{stem}.json"),
            "confidence": None,
            "preprocessing": [],
            "warnings": [],
        })

    manifest = {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "language": args.lang,
        "inputDir": str(input_dir),
        "outputDir": str(ocr_dir),
        "maxPages": args.max_pages,
        "waitMs": args.wait_ms,
        "turnKey": args.turn_key,
        "processor": str(processor) if processor else None,
        "commands": {
            "markdown": markdown_result,
            "json": json_result,
        },
        "pages": pages,
        "warnings": warnings,
    }

    report = [
        "# OCR Report",
        "",
        f"- Input: {input_dir}",
        f"- Output: {ocr_dir}",
        f"- Language: {args.lang}",
        f"- Processor: {processor or 'not found'}",
        f"- Markdown return code: {markdown_result['returncode']}",
        f"- JSON return code: {json_result['returncode']}",
        "",
        "## Warnings",
        "",
    ]
    report.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        report.append("- No wrapper-level OCR warnings.")

    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        print("\n".join(report))
        return 0

    (output / "ocr-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "ocr-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(output / "ocr-manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
