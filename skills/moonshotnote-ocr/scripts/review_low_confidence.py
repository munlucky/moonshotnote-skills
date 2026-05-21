#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a visual review pack for low-confidence OCR lines."
    )
    parser.add_argument("input", help="OCR JSON file or directory containing *.json outputs")
    parser.add_argument("--out", default=None, help="Output directory. Defaults to <input>/low-confidence-review.")
    parser.add_argument("--threshold", type=float, default=0.75, help="Confidence below this value needs review.")
    parser.add_argument("--context-pixels", type=int, default=20, help="Crop padding around the OCR box.")
    parser.add_argument("--max-crops", type=int, default=0, help="Maximum crops to write. 0 means no limit.")
    parser.add_argument("--sheet-size", type=int, default=30, help="Crops per contact sheet.")
    return parser.parse_args()


def iter_json_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")
    return sorted(
        path
        for path in input_path.glob("*.json")
        if path.name not in {"batch_summary.json", "low_confidence_manifest.json"}
    )


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_box(box: Any) -> tuple[int, int, int, int] | None:
    if not box:
        return None

    if isinstance(box, list) and len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
        x1, y1, x2, y2 = box
        return int(x1), int(y1), int(x2), int(y2)

    if isinstance(box, list):
        points: list[tuple[float, float]] = []
        for point in box:
            if isinstance(point, list) and len(point) >= 2:
                try:
                    points.append((float(point[0]), float(point[1])))
                except (TypeError, ValueError):
                    continue
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

    return None


def padded_box(box: tuple[int, int, int, int], image_size: tuple[int, int], padding: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    width, height = image_size
    return (
        max(0, x1 - padding),
        max(0, y1 - padding),
        min(width, x2 + padding),
        min(height, y2 + padding),
    )


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_contact_sheets(crop_paths: list[Path], out_dir: Path, sheet_size: int) -> list[Path]:
    if not crop_paths:
        return []

    sheet_dir = out_dir / "contact-sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    sheets = []
    thumb_width = 360
    thumb_height = 120
    label_height = 24
    cols = 3
    rows = math.ceil(min(sheet_size, len(crop_paths)) / cols)

    for sheet_index, start in enumerate(range(0, len(crop_paths), sheet_size), start=1):
        batch = crop_paths[start : start + sheet_size]
        rows = math.ceil(len(batch) / cols)
        sheet = Image.new("RGB", (cols * thumb_width, rows * (thumb_height + label_height)), "white")
        draw = ImageDraw.Draw(sheet)

        for index, crop_path in enumerate(batch):
            crop = Image.open(crop_path).convert("RGB")
            crop.thumbnail((thumb_width - 16, thumb_height - 8), Image.Resampling.LANCZOS)
            col = index % cols
            row = index // cols
            x = col * thumb_width
            y = row * (thumb_height + label_height)
            draw.text((x + 8, y + 4), crop_path.stem[:46], fill="black")
            sheet.paste(crop, (x + 8, y + label_height))

        sheet_path = sheet_dir / f"low-confidence-sheet-{sheet_index:03d}.png"
        sheet.save(sheet_path)
        sheets.append(sheet_path)

    return sheets


def render_markdown(manifest: dict[str, Any], manifest_path: Path) -> str:
    lines = [
        "# Low-confidence OCR Review",
        "",
        f"- Threshold: `{manifest['threshold']}`",
        f"- Review items: `{manifest['count']}`",
        f"- Crops written: `{manifest['crop_count']}`",
        f"- Manifest: `{manifest_path.name}`",
        "",
        "## Required Closeout",
        "",
        "Check each crop against the source page image. For every item, set `status` in the manifest to one of:",
        "",
        "- `accepted`: OCR text is good enough",
        "- `corrected`: `review_text` contains the corrected text",
        "- `unreadable`: image is not legible enough to recover",
        "- `ignored`: non-content chrome, page number, watermark, decoration, or irrelevant table artifact",
        "",
        "Do not close the OCR task while any item remains `needs_review` unless the user explicitly accepts that risk.",
        "",
        "## Contact Sheets",
        "",
    ]

    for sheet in manifest["contact_sheets"]:
        lines.append(f"- [{Path(sheet).name}]({Path(sheet).as_posix()})")

    lines.extend(["", "## Items", ""])
    for item in manifest["items"]:
        crop = item.get("crop_path") or ""
        lines.append(
            f"- `{item['id']}` conf={item['confidence']:.3f} status={item['status']} "
            f"text=`{item['ocr_text']}` crop=`{Path(crop).name if crop else ''}`"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    out_dir = (
        Path(args.out).expanduser().resolve()
        if args.out
        else (input_path.parent if input_path.is_file() else input_path) / "low-confidence-review"
    )
    crops_dir = out_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    crop_paths: list[Path] = []
    image_cache: dict[Path, Image.Image] = {}

    for json_path in iter_json_files(input_path):
        payload = load_payload(json_path)
        source_image = Path(payload.get("input", ""))
        image = None
        if source_image.exists():
            image = image_cache.get(source_image)
            if image is None:
                image = Image.open(source_image).convert("RGB")
                image_cache[source_image] = image

        for index, raw_item in enumerate(payload.get("items", [])):
            confidence = safe_float(raw_item.get("confidence"))
            if confidence is None or confidence >= args.threshold:
                continue

            item_id = f"lc-{len(items) + 1:05d}"
            crop_path = None
            box = normalize_box(raw_item.get("box"))
            if image is not None and box is not None and (args.max_crops <= 0 or len(crop_paths) < args.max_crops):
                crop_box = padded_box(box, image.size, args.context_pixels)
                crop = image.crop(crop_box)
                crop_path = crops_dir / f"{item_id}__{json_path.stem}__item-{index:04d}.png"
                crop.save(crop_path)
                crop_paths.append(crop_path)

            items.append(
                {
                    "id": item_id,
                    "status": "needs_review",
                    "ocr_text": raw_item.get("text") or "",
                    "review_text": "",
                    "confidence": confidence,
                    "box": raw_item.get("box"),
                    "source_image": str(source_image) if source_image else "",
                    "ocr_json": str(json_path),
                    "crop_path": str(crop_path) if crop_path else "",
                    "notes": "",
                }
            )

    contact_sheets = write_contact_sheets(crop_paths, out_dir, args.sheet_size)
    manifest = {
        "threshold": args.threshold,
        "count": len(items),
        "crop_count": len(crop_paths),
        "status_counts": {"needs_review": len(items)},
        "contact_sheets": [str(path) for path in contact_sheets],
        "items": items,
    }
    manifest_path = out_dir / "low_confidence_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "low_confidence_review.md").write_text(render_markdown(manifest, manifest_path), encoding="utf-8")

    print(json.dumps({key: manifest[key] for key in ("threshold", "count", "crop_count", "status_counts")}, indent=2))
    print(str(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
