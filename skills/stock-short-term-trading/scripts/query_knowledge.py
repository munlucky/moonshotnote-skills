#!/usr/bin/env python3
"""Query the public-safe knowledge references for this skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def score(row: dict, terms: list[str]) -> int:
    haystack = " ".join(
        str(row.get(key, ""))
        for key in ("id", "title", "name", "summary", "aliases", "keywords", "type")
    ).lower()
    return sum(haystack.count(term.lower()) for term in terms)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search public-safe trading knowledge.")
    parser.add_argument("--query", required=True, help="Korean or English search terms")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    refs = root / "references"
    terms = [term for term in args.query.replace(",", " ").split() if term]

    rows: list[tuple[str, int, dict]] = []
    for label, filename in (
        ("chunk", "chunks.jsonl"),
        ("node", "nodes.jsonl"),
        ("edge", "edges.jsonl"),
    ):
        for row in load_jsonl(refs / filename):
            row_score = score(row, terms)
            if row_score > 0:
                rows.append((label, row_score, row))

    rows.sort(key=lambda item: item[1], reverse=True)
    for label, row_score, row in rows[: args.limit]:
        name = row.get("title") or row.get("name") or f"{row.get('source')} -> {row.get('target')}"
        print(f"[{label} score={row_score}] {name}")
        print(f"  id: {row.get('id', '')}")
        print(f"  summary: {row.get('summary', '')}")
        print(f"  refs: {json.dumps(row.get('source_refs', []), ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
