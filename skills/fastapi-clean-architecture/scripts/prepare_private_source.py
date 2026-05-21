#!/usr/bin/env python3
"""Create ignored local source metadata and private OCR chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def chunk_lines(text: str, size: int) -> list[dict]:
    lines = text.splitlines()
    chunks = []
    for start in range(0, len(lines), size):
        block = lines[start : start + size]
        chunks.append(
            {
                "id": f"private-lines-{start + 1:05d}-{start + len(block):05d}",
                "line_start": start + 1,
                "line_end": start + len(block),
                "text": "\n".join(block),
            }
        )
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-ocr", required=True)
    parser.add_argument("--closeout", required=True)
    parser.add_argument("--out-dir", default=Path(__file__).resolve().parents[1] / "output" / "private-source")
    parser.add_argument("--chunk-lines", type=int, default=120)
    args = parser.parse_args()

    reviewed_ocr = Path(args.reviewed_ocr).resolve()
    closeout = Path(args.closeout).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    closeout_data = json.loads(closeout.read_text(encoding="utf-8"))
    text = reviewed_ocr.read_text(encoding="utf-8")
    chunks = chunk_lines(text, args.chunk_lines)

    chunk_path = out_dir / "private_chunks.jsonl"
    with chunk_path.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_ocr": str(reviewed_ocr),
        "review_closeout": str(closeout),
        "reviewed_ocr_sha256": sha256(reviewed_ocr),
        "needs_review_remaining": closeout_data.get("needs_review_remaining"),
        "page_count": closeout_data.get("page_count"),
        "reviewed_line_total": closeout_data.get("reviewed_line_total"),
        "private_chunks": str(chunk_path),
        "private_chunk_count": len(chunks),
        "tracked_public_graph_contains_raw_ocr": False,
    }
    manifest_path = out_dir / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
