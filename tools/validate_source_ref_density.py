#!/usr/bin/env python3
"""Validate that public graph growth is backed by source reference coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def refs(row: dict) -> list[dict]:
    return [item for item in row.get("source_refs", []) if isinstance(item, dict)]


def validate_skill(root: Path, skill: str, min_unique_ref_ratio: float) -> None:
    refs_dir = root / "skills" / skill / "references"
    rows = load_jsonl(refs_dir / "nodes.jsonl") + load_jsonl(refs_dir / "edges.jsonl") + load_jsonl(refs_dir / "chunks.jsonl")
    if not rows:
        raise ValueError(f"{skill}: no public rows")
    unique_refs = set()
    ref_rows = 0
    for row in rows:
        row_refs = refs(row)
        if row_refs:
            ref_rows += 1
        for ref in row_refs:
            if skill == "backend-architecture":
                unique_refs.add((ref.get("source_skill"), ref.get("source_id")))
            else:
                unique_refs.add((ref.get("source_id"), ref.get("chapter"), tuple(ref.get("line_range") or ref.get("lines") or [])))
    if ref_rows != len(rows):
        raise ValueError(f"{skill}: {len(rows) - ref_rows} rows missing source_refs")
    ratio = len(unique_refs) / len(rows)
    if ratio < min_unique_ref_ratio:
        raise ValueError(f"{skill}: unique source_ref ratio {ratio:.2f} below {min_unique_ref_ratio:.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--min-unique-ref-ratio", type=float, default=0.18)
    args = parser.parse_args()
    try:
        root = Path(args.repo_root)
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            validate_skill(root, skill, args.min_unique_ref_ratio)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Source reference density valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
