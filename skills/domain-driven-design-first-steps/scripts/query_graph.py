#!/usr/bin/env python3
"""Keyword query over the public-safe DDD knowledge graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score_row(row: dict, terms: list[str]) -> int:
    haystack = " ".join(
        str(row.get(key, ""))
        for key in ("id", "type", "name", "summary", "aliases", "keywords", "source", "target")
    ).lower()
    return sum(1 for term in terms if term in haystack)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--q", required=True, help="Korean or English search terms")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    terms = [term.lower() for term in args.q.split() if term.strip()]
    rows: list[dict] = []
    for kind, filename in (("node", "nodes.jsonl"), ("edge", "edges.jsonl"), ("chunk", "chunks.jsonl")):
        for row in load_jsonl(REFERENCES / filename):
            score = score_row(row, terms)
            if score:
                rows.append({"kind": kind, "score": score, **row})

    for row in sorted(rows, key=lambda item: (-item["score"], item.get("id", item.get("source", ""))))[: args.limit]:
        label = row.get("id") or f"{row.get('source')}->{row.get('target')}"
        print(f"[{row['kind']}] {label}: {row.get('name') or row.get('title') or row.get('type')}")
        print(f"  {row['summary']}")
        print(f"  refs={row['source_refs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
