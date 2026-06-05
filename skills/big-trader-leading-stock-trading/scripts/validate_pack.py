#!/usr/bin/env python3
"""Local structural checks for this skill package."""
from __future__ import annotations

import json
from pathlib import Path

REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/ontology.yaml",
    "references/graph_manifest.json",
    "references/nodes.jsonl",
    "references/edges.jsonl",
    "references/chunks.jsonl",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    if missing:
        raise SystemExit("missing files: " + ", ".join(missing))
    manifest = json.loads((root / "references/graph_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("public_sanitized") is not True:
        raise SystemExit("public_sanitized must be true")
    private_location = root / manifest.get("private_source_location", "")
    if private_location.exists() and not private_location.is_dir():
        raise SystemExit("private source location exists but is not a directory")
    print("Local skill package checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
