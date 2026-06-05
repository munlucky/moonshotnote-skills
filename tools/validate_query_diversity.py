#!/usr/bin/env python3
"""Validate query QA fixtures are not concentrated on a few artifacts."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_skill(root: Path, skill: str, max_share: float) -> None:
    rows = load_jsonl(root / "skills" / skill / "references" / "query_qa.jsonl")
    node_counts: collections.Counter[str] = collections.Counter()
    chunk_counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        node_counts.update(row.get("expected_nodes", []))
        chunk_counts.update(row.get("expected_chunks", []))
    if not node_counts or not chunk_counts:
        raise ValueError(f"{skill}: query QA must reference nodes and chunks")
    node_share = max(node_counts.values()) / len(rows)
    chunk_share = max(chunk_counts.values()) / len(rows)
    if node_share > max_share:
        raise ValueError(f"{skill}: one node appears in {node_share:.0%} of query QA rows")
    if chunk_share > max_share:
        raise ValueError(f"{skill}: one chunk appears in {chunk_share:.0%} of query QA rows")
    if len(node_counts) < min(12, len(rows) // 2):
        raise ValueError(f"{skill}: query QA references too few distinct nodes")
    if len(chunk_counts) < min(8, len(rows) // 3):
        raise ValueError(f"{skill}: query QA references too few distinct chunks")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--max-share", type=float, default=0.18)
    args = parser.parse_args()
    try:
        root = Path(args.repo_root)
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            validate_skill(root, skill, args.max_share)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Query diversity valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
