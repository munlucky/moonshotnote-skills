#!/usr/bin/env python3
"""Capture paginated browser ebook screenshots with agent-browser."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
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


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture all visible ebook pages.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", default="", help="Optional URL to open before capture.")
    parser.add_argument("--output", default=".", help="Run output directory.")
    parser.add_argument("--lang", default="kor+eng", help="OCR language hint recorded in manifest.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum pages to capture. Use an explicit full-book bound.")
    parser.add_argument("--wait-ms", type=int, default=700, help="Delay after page turn.")
    parser.add_argument("--turn-key", default="ArrowRight", help="Key sent after each screenshot.")
    args = parser.parse_args()

    if args.max_pages < 1:
        raise SystemExit("--max-pages must be at least 1 for capture.")

    output = Path(args.output)
    captures = output / "captures"
    if not args.dry_run:
        captures.mkdir(parents=True, exist_ok=True)

    commands: list[dict[str, Any]] = []
    if args.input:
        commands.append(run_command(["agent-browser", "open", args.input], args.dry_run))
        if not args.dry_run:
            time.sleep(args.wait_ms / 1000)

    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "bookTitle": "unknown",
        "sourceUrl": args.input,
        "captureStartedAt": datetime.now(timezone.utc).isoformat(),
        "captureFinishedAt": None,
        "turnKey": args.turn_key,
        "waitMs": args.wait_ms,
        "language": args.lang,
        "viewport": {"width": None, "height": None},
        "pages": [],
        "warnings": [],
        "commands": commands,
    }

    previous_hash: str | None = None
    for index in range(1, args.max_pages + 1):
        page_name = f"page-{index:04d}.png"
        image_path = captures / page_name
        url_result = run_command(["agent-browser", "get", "url"], args.dry_run)
        title_result = run_command(["agent-browser", "get", "title"], args.dry_run)
        shot_result = run_command(["agent-browser", "screenshot", str(image_path)], args.dry_run)
        page_hash = None if args.dry_run else sha256_file(image_path)

        warnings: list[str] = []
        if shot_result["returncode"] not in (0, None):
            warnings.append("screenshot-command-failed")
        if not args.dry_run and not image_path.exists():
            warnings.append("screenshot-file-missing")
        if page_hash and previous_hash == page_hash:
            warnings.append("duplicate-of-previous-page")

        manifest["pages"].append({
            "pageIndex": index,
            "imagePath": f"captures/{page_name}",
            "textPath": None,
            "method": "capture",
            "hash": page_hash,
            "url": url_result.get("stdout", "").strip(),
            "title": title_result.get("stdout", "").strip(),
            "warnings": warnings,
        })
        manifest["commands"].extend([url_result, title_result, shot_result])

        if page_hash and previous_hash == page_hash:
            manifest["warnings"].append(f"Stopped after page {index}: screenshot hash repeated after a page turn.")
            break
        previous_hash = page_hash

        if index < args.max_pages:
            press_result = run_command(["agent-browser", "press", args.turn_key], args.dry_run)
            manifest["commands"].append(press_result)
            if not args.dry_run:
                time.sleep(args.wait_ms / 1000)

    manifest["captureFinishedAt"] = datetime.now(timezone.utc).isoformat()

    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    manifest_path = output / "capture-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
