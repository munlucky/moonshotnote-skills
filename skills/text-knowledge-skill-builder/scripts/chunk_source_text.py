#!/usr/bin/env python3
"""Create private line-based chunks from a source text file."""

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


def chunk_lines(lines: list[str], chunk_size: int, overlap: int) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")
    chunks: list[dict] = []
    start = 0
    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunks.append(
            {
                "id": f"source-lines-{start + 1:05d}-{end:05d}",
                "line_start": start + 1,
                "line_end": end,
                "text": "\n".join(lines[start:end]),
            }
        )
        if end == len(lines):
            break
        start = end - overlap
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to source text")
    parser.add_argument("--out-dir", required=True, help="Ignored private-source output directory")
    parser.add_argument("--chunk-lines", type=int, default=120)
    parser.add_argument("--overlap-lines", type=int, default=20)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = source.read_text(encoding="utf-8").splitlines()
    chunks = chunk_lines(lines, args.chunk_lines, args.overlap_lines)

    chunks_path = out_dir / "source_chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_basename": source.name,
        "source_sha256": sha256(source),
        "line_count": len(lines),
        "chunk_count": len(chunks),
        "chunk_lines": args.chunk_lines,
        "overlap_lines": args.overlap_lines,
        "chunks": str(chunks_path),
        "tracked_public_package_contains_raw_source": False,
    }
    manifest_path = out_dir / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
