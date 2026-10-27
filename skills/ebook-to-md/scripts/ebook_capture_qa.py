#!/usr/bin/env python3
"""Validate ebook capture manifests and screenshot files."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def png_size(path: Path) -> tuple[int | None, int | None]:
    if not path.exists():
        return (None, None)
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) >= 24 and header.startswith(b"\x89PNG\r\n\x1a\n") and header[12:16] == b"IHDR":
        return struct.unpack(">II", header[16:24])
    return (None, None)


def load_manifest(input_path: Path) -> tuple[dict[str, Any], Path]:
    if input_path.is_dir():
        manifest_path = input_path / "capture-manifest.json"
    else:
        manifest_path = input_path
    return json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run QA checks over ebook captures.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", default="capture-manifest.json", help="Manifest path or run directory.")
    parser.add_argument("--output", default=".", help="Directory for capture-report.md.")
    parser.add_argument("--lang", default="kor+eng", help="OCR language hint recorded for consistency.")
    parser.add_argument("--max-pages", type=int, default=0, help="Optional expected maximum pages; 0 means no bound check.")
    parser.add_argument("--wait-ms", type=int, default=700, help="Recorded wait time for consistency.")
    parser.add_argument("--turn-key", default="ArrowRight", help="Recorded turn key for consistency.")
    args = parser.parse_args()

    manifest, run_dir = load_manifest(Path(args.input))
    pages = manifest.get("pages", [])
    hash_counts = Counter(page.get("hash") for page in pages if page.get("hash"))
    url_counts = Counter(page.get("url") for page in pages if page.get("url"))
    dimensions: Counter[tuple[int | None, int | None]] = Counter()
    report_lines = [
        "# Capture QA Report",
        "",
        f"- Pages inspected: {len(pages)}",
        f"- Language hint: {args.lang}",
        f"- Turn key: {args.turn_key}",
        f"- Wait ms: {args.wait_ms}",
        "",
        "## Findings",
        "",
    ]
    findings: list[str] = []

    for page in pages:
        page_warnings = list(page.get("warnings") or [])
        image_rel = page.get("imagePath")
        image_path = run_dir / image_rel if image_rel else None
        if not image_path or not image_path.exists():
            page_warnings.append("missing-image")
        else:
            size = image_path.stat().st_size
            if size < 10_000:
                page_warnings.append("suspiciously-small-image")
            width, height = png_size(image_path)
            dimensions[(width, height)] += 1
            if width is None or height is None:
                page_warnings.append("not-a-readable-png")
            elif width < 400 or height < 400:
                page_warnings.append("suspiciously-small-dimensions")
            actual_hash = sha256_file(image_path)
            if page.get("hash") and actual_hash != page.get("hash"):
                page_warnings.append("hash-mismatch")
            if actual_hash and hash_counts[actual_hash] > 1:
                page_warnings.append("duplicate-hash")

        if page.get("url") and url_counts[page["url"]] > max(3, len(pages) // 2):
            page_warnings.append("url-repeats-across-many-pages")

        if page_warnings:
            findings.append(f"- Page {page.get('pageIndex')}: {', '.join(sorted(set(page_warnings)))}")
            page["warnings"] = sorted(set(page_warnings))

    if args.max_pages and len(pages) > args.max_pages:
        findings.append(f"- Page count {len(pages)} exceeds --max-pages {args.max_pages}.")
    if len(dimensions) > 1:
        findings.append(f"- Screenshot dimensions vary: {dict(dimensions)}")
    duplicate_hashes = [value for value, count in hash_counts.items() if count > 1]
    if duplicate_hashes:
        findings.append(f"- Duplicate screenshot hashes found: {len(duplicate_hashes)}")

    if findings:
        report_lines.extend(findings)
    else:
        report_lines.append("- No blocking capture QA findings detected by metadata checks.")

    report = "\n".join(report_lines) + "\n"
    if args.dry_run:
        print(report)
        return 0

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "capture-report.md").write_text(report, encoding="utf-8")
    (run_dir / "capture-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output / "capture-report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
