#!/usr/bin/env python3
"""Inspect an open browser ebook through agent-browser."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_command(args: list[str], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"command": args, "returncode": None, "stdout": "", "stderr": "", "dryRun": True}
    try:
        proc = subprocess.run(args, text=True, capture_output=True, check=False)
        return {
            "command": args,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "dryRun": False,
        }
    except FileNotFoundError as exc:
        return {"command": args, "returncode": 127, "stdout": "", "stderr": str(exc), "dryRun": False}


def classify(report: dict[str, Any]) -> dict[str, Any]:
    body_text = report.get("commands", {}).get("bodyText", {}).get("stdout", "")
    iframe_eval = report.get("commands", {}).get("iframeInventory", {}).get("stdout", "")
    viewer_eval = report.get("commands", {}).get("viewerMarkers", {}).get("stdout", "")
    body_len = len(body_text.strip())
    structured_possible = body_len >= 800 or "sameOrigin" in iframe_eval or "epub" in viewer_eval.lower()
    return {
        "bodyTextLength": body_len,
        "structuredExtractionLikely": structured_possible,
        "recommendedNextStep": "structured-extract" if structured_possible else "capture-all",
        "warnings": [] if structured_possible else ["Body text is short or unavailable; prepare screenshot capture fallback."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a browser ebook with agent-browser.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", default="", help="Optional URL to open before inspection.")
    parser.add_argument("--output", default=".", help="Run output directory.")
    parser.add_argument("--lang", default="kor+eng", help="OCR language hint recorded for downstream stages.")
    parser.add_argument("--max-pages", type=int, default=5, help="Recorded smoke-test page bound.")
    parser.add_argument("--wait-ms", type=int, default=700, help="Recorded wait time for page turns.")
    parser.add_argument("--turn-key", default="ArrowRight", help="Recorded key used for page turns.")
    args = parser.parse_args()

    output = Path(args.output)
    if not args.dry_run:
        output.mkdir(parents=True, exist_ok=True)

    commands: dict[str, dict[str, Any]] = {}
    commands["coreHelp"] = run_command(["agent-browser", "skills", "get", "core"], args.dry_run)
    if args.input:
        commands["open"] = run_command(["agent-browser", "open", args.input], args.dry_run)
    commands["url"] = run_command(["agent-browser", "get", "url"], args.dry_run)
    commands["title"] = run_command(["agent-browser", "get", "title"], args.dry_run)
    commands["snapshot"] = run_command(["agent-browser", "snapshot"], args.dry_run)
    commands["bodyText"] = run_command(["agent-browser", "get", "text", "body"], args.dry_run)
    commands["bodyHtml"] = run_command(["agent-browser", "get", "html", "body"], args.dry_run)
    commands["iframeInventory"] = run_command([
        "agent-browser",
        "eval",
        "JSON.stringify(Array.from(document.querySelectorAll('iframe')).map((f,i)=>({index:i,src:f.src,width:f.clientWidth,height:f.clientHeight,sameOrigin:(()=>{try{return !!f.contentDocument}catch(e){return false}})()})))",
    ], args.dry_run)
    commands["viewerMarkers"] = run_command([
        "agent-browser",
        "eval",
        "JSON.stringify({hasEpub:!!window.ePub,hasRendition:!!window.rendition,hasReadium:!!(window.Readium||navigator.epubReadingSystem),canvasCount:document.querySelectorAll('canvas').length,imageCount:document.images.length,iframeCount:document.querySelectorAll('iframe').length})",
    ], args.dry_run)

    report: dict[str, Any] = {
        "schemaVersion": 1,
        "inspectedAt": datetime.now(timezone.utc).isoformat(),
        "input": args.input,
        "output": str(output),
        "language": args.lang,
        "maxPages": args.max_pages,
        "waitMs": args.wait_ms,
        "turnKey": args.turn_key,
        "commands": commands,
    }
    report["decision"] = classify(report)

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    (output / "inspect-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output / "inspect-report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
