#!/usr/bin/env python3
"""Keyword search over the public knowledge pack."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def haystack(row: dict) -> str:
    values: list[str] = []
    for key in ("id", "type", "name", "title", "summary"):
        if key in row:
            values.append(str(row[key]))
    values.extend(str(item) for item in row.get("aliases", []))
    values.extend(str(item) for item in row.get("keywords", []))
    return " ".join(values).lower()


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/query_knowledge.py <keyword>")
        return 2

    query = " ".join(sys.argv[1:]).lower()
    rows = []
    for label, filename in (("node", "nodes.jsonl"), ("chunk", "chunks.jsonl")):
        for row in load_jsonl(REFS / filename):
            if query in haystack(row):
                rows.append((label, row))

    for label, row in rows:
        name = row.get("name") or row.get("title")
        print(f"[{label}] {row['id']} - {name}")
        print(f"  {row['summary']}")
        refs = ", ".join(f"{ref['source']}:{ref['lines'][0]}-{ref['lines'][1]}" for ref in row["source_refs"])
        print(f"  refs: {refs}")

    if not rows:
        print("No public knowledge rows matched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
