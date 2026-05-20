#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OcrItem:
    text: str
    confidence: float | None = None
    box: Any | None = None
    raw: Any | None = None


@dataclass
class OcrResult:
    engine: str
    input_path: Path
    items: list[OcrItem]
    raw: Any | None = None
    warnings: list[str] | None = None

    @property
    def text(self) -> str:
        lines = []
        for item in self.items:
            if not item.text:
                continue
            if item.confidence is not None and item.confidence < 0.75:
                lines.append("[unclear]")
            else:
                lines.append(item.text)
        return "\n".join(lines)


@dataclass
class PaddleRunner:
    ocr: Any
    mode: str
    warnings: list[str]


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR an image or image directory with PaddleOCR or Surya.")
    parser.add_argument("input", help="Input image path or directory")
    parser.add_argument("--engine", choices=["auto", "paddle", "surya"], default="auto")
    parser.add_argument("--lang", default="korean", help="PaddleOCR language")
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory. Defaults to <input-dir>/ocr-output/<engine>.",
    )
    parser.add_argument("--pattern", default="*.png", help="Glob pattern when input is a directory")
    parser.add_argument("--recursive", action="store_true", help="Search directory recursively")
    parser.add_argument("--json", action="store_true", help="Write structured JSON evidence per image")
    parser.add_argument("--md", action="store_true", help="Write markdown review report per image")
    parser.add_argument("--summary", action="store_true", help="Write batch_summary.json")
    parser.add_argument("--all", action="store_true", help="Write txt, json, md, and batch summary")
    parser.add_argument("--fail-fast", action="store_true", help="Stop batch processing on the first failed image")
    return parser.parse_args()


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_paddle_result(result: Any) -> list[OcrItem]:
    items: list[OcrItem] = []

    for page in result or []:
        if hasattr(page, "json"):
            data = page.json
            extracted = extract_from_mapping(data)
            if extracted:
                items.extend(extracted)
            else:
                items.append(OcrItem(text=str(data), raw=data))
            continue

        if isinstance(page, dict):
            extracted = extract_from_mapping(page)
            if extracted:
                items.extend(extracted)
            else:
                items.append(OcrItem(text=json.dumps(page, ensure_ascii=False), raw=page))
            continue

        if isinstance(page, list):
            for entry in page:
                parsed = parse_legacy_paddle_entry(entry)
                items.append(parsed)
            continue

        items.append(OcrItem(text=str(page), raw=page))

    return items


def extract_from_mapping(data: dict[str, Any]) -> list[OcrItem]:
    if isinstance(data.get("res"), dict):
        data = data["res"]

    texts = data.get("rec_texts") or data.get("texts") or data.get("text")
    scores = data.get("rec_scores") or data.get("scores") or data.get("confidence")
    boxes = data.get("rec_boxes") or data.get("dt_polys") or data.get("boxes")

    if isinstance(texts, str):
        return [OcrItem(text=texts, confidence=safe_float(scores), box=boxes)]

    if not isinstance(texts, list):
        return []

    output = []
    for index, text in enumerate(texts):
        confidence = scores[index] if isinstance(scores, list) and index < len(scores) else None
        box = boxes[index] if isinstance(boxes, list) and index < len(boxes) else None
        output.append(OcrItem(text=str(text), confidence=safe_float(confidence), box=box))
    return output


def parse_legacy_paddle_entry(entry: Any) -> OcrItem:
    try:
        box = entry[0]
        text = entry[1][0]
        confidence = safe_float(entry[1][1])
        return OcrItem(text=str(text), confidence=confidence, box=box, raw=entry)
    except Exception:
        return OcrItem(text=str(entry), raw=entry)


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
    )


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def resolve_cli(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found

    scripts_dir = Path(sys.executable).resolve().parent
    for candidate in (scripts_dir / name, scripts_dir / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return None


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
                items = [OcrItem(text=text or "[unclear]")]
            return OcrResult(
                engine="surya",
                input_path=input_path,
                items=items,
                raw={"attempts": attempts},
                warnings=["Surya CLI output shape can vary by version; inspect JSON output for details."],
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
    for page in pages:
        if not isinstance(page, dict):
            continue
        for line in page.get("text_lines", []):
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
                )
            )
    return items


def collect_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(collect_text(item))
        return output
    if isinstance(value, dict):
        output = []
        for key in ("text", "html", "markdown"):
            if isinstance(value.get(key), str):
                output.append(value[key])
        for item in value.values():
            if isinstance(item, (dict, list)):
                output.extend(collect_text(item))
        return output
    return []


def low_confidence_items(items: list[OcrItem]) -> list[str]:
    suspicious = []
    for item in items:
        if item.confidence is not None and item.confidence < 0.75:
            suspicious.append(item.text or "[unclear]")
    return suspicious


def write_outputs(result: OcrResult, out_dir: Path, args: argparse.Namespace) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = result.input_path.stem
    prefix = f"{stem}.{result.engine}"
    txt_path = out_dir / f"{prefix}.txt"
    json_path = out_dir / f"{prefix}.json"
    md_path = out_dir / f"{prefix}.md"

    text = result.text
    if not text.strip():
        text = "[unclear]"

    payload = {
        "engine": result.engine,
        "input": str(result.input_path),
        "text": text,
        "items": [
            {
                "text": item.text,
                "confidence": item.confidence,
                "box": item.box,
                "raw": item.raw,
            }
            for item in result.items
        ],
        "warnings": result.warnings or [],
        "low_confidence": low_confidence_items(result.items),
    }

    txt_path.write_text(text + "\n", encoding="utf-8")
    written = {"txt": txt_path}
    if args.json or args.all:
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        written["json"] = json_path
    if args.md or args.all:
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        written["md"] = md_path
    return written


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


def default_out_dir(input_path: Path, engine: str) -> Path:
    root = input_path if input_path.is_dir() else input_path.parent
    return root / "ocr-output" / engine


def run_one(
    image_path: Path,
    args: argparse.Namespace,
    out_dir: Path,
    paddle_runner: PaddleRunner | None,
) -> dict[str, Any]:
    if args.engine == "paddle":
        result = run_paddle(image_path, args.lang, paddle_runner)
    elif args.engine == "surya":
        result = run_surya(image_path, out_dir)
    else:
        try:
            result = run_paddle(image_path, args.lang, paddle_runner)
            if not result.text.strip():
                result = run_surya(image_path, out_dir)
        except Exception as paddle_error:
            try:
                result = run_surya(image_path, out_dir)
                result.warnings = (result.warnings or []) + [f"PaddleOCR fallback reason: {paddle_error}"]
            except Exception as surya_error:
                raise RuntimeError(
                    f"Both OCR engines failed. PaddleOCR: {paddle_error}; Surya: {surya_error}"
                ) from surya_error

    written = write_outputs(result, out_dir, args)
    return {
        "input": str(image_path),
        "ok": True,
        "engine": result.engine,
        "outputs": {key: str(value) for key, value in written.items()},
        "line_count": len(result.text.splitlines()),
        "low_confidence_count": len(low_confidence_items(result.items)),
        "warnings": result.warnings or [],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    low_confidence = payload["low_confidence"]
    warnings = payload["warnings"]
    parts = [
        f"# OCR Result: {Path(payload['input']).name}",
        "",
        f"- Engine: {payload['engine']}",
        f"- Input: `{payload['input']}`",
    ]
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
