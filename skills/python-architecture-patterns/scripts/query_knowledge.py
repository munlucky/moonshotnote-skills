#!/usr/bin/env python3
"""Query the public-safe knowledge pack by keyword."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def score_row(row: dict, query_terms: list[str]) -> int:
    haystack = " ".join(
        str(value)
        for key, value in row.items()
        if key not in {"source_refs", "public_safe"}
    ).lower()
    return sum(1 for term in query_terms if term in haystack)


def query_terms(raw_terms: list[str]) -> list[str]:
    terms: list[str] = []
    for raw in raw_terms:
        value = raw.strip().lower()
        if not value:
            continue
        terms.append(value)
        if " " in value:
            terms.append(value.replace(" ", "-"))
        terms.extend(part for part in re.split(r"[\s-]+", value) if part)
    return sorted(set(terms))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+", help="Keyword query")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    terms = query_terms(args.query)
    rows = []
    for kind, filename in (("node", "nodes.jsonl"), ("chunk", "chunks.jsonl")):
        for row in load_jsonl(REFERENCES / filename):
            score = score_row(row, terms)
            if score:
                rows.append((score, kind, row))

    for score, kind, row in sorted(rows, key=lambda item: (-item[0], item[1], item[2].get("id", "")))[: args.limit]:
        refs = ", ".join(
            f"{ref.get('source_id') or ref.get('source')}:{ref.get('lines') or ref.get('line_range')}"
            for ref in row.get("source_refs", [])
        )
        print(f"[{kind}] {row.get('id')} score={score}")
        print(f"name: {row.get('name') or row.get('title')}")
        print(f"summary: {row.get('summary')}")
        print(f"source_refs: {refs}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
