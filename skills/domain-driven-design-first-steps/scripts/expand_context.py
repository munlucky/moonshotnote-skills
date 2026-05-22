#!/usr/bin/env python3
"""Expand one node with direct graph relationships."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True, help="Node id to expand")
    args = parser.parse_args()

    nodes = {row["id"]: row for row in load_jsonl(REFERENCES / "nodes.jsonl")}
    edges = load_jsonl(REFERENCES / "edges.jsonl")
    node = nodes.get(args.node)
    if not node:
        print(f"Unknown node: {args.node}")
        return 1

    print(f"# {node['name']} ({node['id']})")
    print(node["summary"])
    print(f"refs={node['source_refs']}")
    print()
    print("## Relationships")
    for edge in edges:
        if edge["source"] == args.node or edge["target"] == args.node:
            direction = "out" if edge["source"] == args.node else "in"
            other_id = edge["target"] if direction == "out" else edge["source"]
            other = nodes.get(other_id, {"name": other_id})
            print(f"- {direction} {edge['type']} {other_id} ({other['name']}): {edge['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
