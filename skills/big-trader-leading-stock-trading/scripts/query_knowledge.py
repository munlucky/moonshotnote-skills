#!/usr/bin/env python3
"""Keyword search over the public-safe knowledge pack."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def score(row: dict, query: str) -> int:
    haystack = " ".join(str(row.get(key, "")) for key in ("id", "type", "name", "title", "summary"))
    haystack += " " + " ".join(row.get("aliases", []) or row.get("keywords", []))
    terms = [term for term in query.lower().split() if term]
    text = haystack.lower()
    return sum(text.count(term) for term in terms)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    root = Path(args.root)
    refs = root / "references"
    rows = []
    for kind, filename in (("node", "nodes.jsonl"), ("edge", "edges.jsonl"), ("chunk", "chunks.jsonl")):
        for row in load_jsonl(refs / filename):
            value = score(row, args.query)
            if value:
                rows.append((value, kind, row))

    rows.sort(key=lambda item: (-item[0], item[1], item[2].get("id", "")))
    for value, kind, row in rows[: args.limit]:
        label = row.get("name") or row.get("title") or row.get("id")
        print(f"[{kind}:{value}] {label}")
        print(row.get("summary", ""))
        print("source_refs=", json.dumps(row.get("source_refs", []), ensure_ascii=False))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
