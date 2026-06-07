#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ocr_pipeline.engines.paddle import create_paddle_runner
from ocr_pipeline.output import low_confidence_items, write_outputs
from ocr_pipeline.router import ENGINES, run_ocr
from ocr_pipeline.utils import IMAGE_EXTENSIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR an image or image directory with PaddleOCR, PP-StructureV3, or Surya.")
    parser.add_argument("input", help="Input image path or directory")
    parser.add_argument("--engine", choices=sorted(ENGINES), default="auto")
    parser.add_argument("--page-mode", choices=["auto", "plain-text", "table", "multi-column", "layout", "unknown"], default="auto")
    parser.add_argument("--lang", default="korean", help="PaddleOCR language")
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory. Defaults to <input-dir>/ocr-output/<requested-engine>.",
    )
    parser.add_argument("--pattern", default="*.png", help="Glob pattern when input is a directory")
    parser.add_argument("--recursive", action="store_true", help="Search directory recursively")
    parser.add_argument("--json", action="store_true", help="Write structured JSON evidence per image")
    parser.add_argument("--md", action="store_true", help="Write markdown review report per image")
    parser.add_argument("--summary", action="store_true", help="Write batch_summary.json")
    parser.add_argument("--all", action="store_true", help="Write txt, json, md, and batch summary")
    parser.add_argument("--fail-fast", action="store_true", help="Stop batch processing on the first failed image")
    return parser.parse_args()


def iter_input_paths(input_path: Path, pattern: str, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    candidates = input_path.rglob(pattern) if recursive else input_path.glob(pattern)
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def output_dir_for(input_root: Path, image_path: Path, out_dir: Path) -> Path:
    if input_root.is_file():
        return out_dir
    try:
        relative_parent = image_path.parent.relative_to(input_root)
    except ValueError:
        relative_parent = Path()
    return out_dir / relative_parent


def default_out_dir(input_path: Path, requested_engine: str) -> Path:
    root = input_path if input_path.is_dir() else input_path.parent
    return root / "ocr-output" / requested_engine


def run_one(
    image_path: Path,
    args: argparse.Namespace,
    out_dir: Path,
    paddle_runner: Any | None,
) -> dict[str, Any]:
    result = run_ocr(
        image_path,
        engine=args.engine,
        page_mode=args.page_mode,
        lang=args.lang,
        out_dir=out_dir,
        paddle_runner=paddle_runner,
    )
    written = write_outputs(result, out_dir, args)
    return {
        "input": str(image_path),
        "ok": True,
        "engine": result.engine,
        "requested_engine": args.engine,
        "fallback_used": result.fallback_used,
        "fallback_reason": result.fallback_reason,
        "page_type": result.page_type,
        "page_type_confidence": result.page_type_confidence,
        "outputs": {key: str(value) for key, value in written.items()},
        "line_count": len(result.text.splitlines()),
        "low_confidence_count": len(low_confidence_items(result.items)),
        "warnings": result.warnings or [],
    }


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    out_dir = (
        Path(args.out).expanduser().resolve()
        if args.out
        else default_out_dir(input_path, args.engine).resolve()
    )

    try:
        image_paths = iter_input_paths(input_path, args.pattern, args.recursive)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not image_paths:
        print(f"No images matched: {input_path} / {args.pattern}", file=sys.stderr)
        return 2

    try:
        paddle_runner = create_paddle_runner(args.lang) if args.engine in {"auto", "paddle"} else None
        batch = []
        for image_path in image_paths:
            target_out_dir = output_dir_for(input_path, image_path, out_dir)
            try:
                batch.append(run_one(image_path, args, target_out_dir, paddle_runner))
            except Exception as item_exc:
                failure = {
                    "input": str(image_path),
                    "ok": False,
                    "engine": args.engine,
                    "requested_engine": args.engine,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "page_type": args.page_mode,
                    "page_type_confidence": 0.0,
                    "error": str(item_exc),
                    "outputs": {},
                    "line_count": 0,
                    "low_confidence_count": 0,
                    "warnings": [],
                }
                batch.append(failure)
                if args.fail_fast:
                    break

        summary = {
            "input": str(input_path),
            "out": str(out_dir),
            "engine": args.engine,
            "requested_engine": args.engine,
            "page_mode": args.page_mode,
            "actual_engines": sorted({item.get("engine") for item in batch if item.get("ok")}),
            "count": len(batch),
            "ok_count": len([item for item in batch if item.get("ok")]),
            "error_count": len([item for item in batch if not item.get("ok")]),
            "items": batch,
        }
        if args.summary or args.all:
            out_dir.mkdir(parents=True, exist_ok=True)
            summary_path = out_dir / "batch_summary.json"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            summary["summary"] = str(summary_path)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if summary["error_count"] else 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
