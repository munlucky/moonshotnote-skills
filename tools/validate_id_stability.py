#!/usr/bin/env python3
"""Validate that existing public IDs have not been accidentally deleted."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_ids(path: Path, edge: bool = False) -> set[str]:
    if not path.is_file():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ids.add(f"{row.get('source')}->{row.get('target')}" if edge else row["id"])
    return ids


def validate_skill(root: Path, skill: str, baseline_root: Path | None) -> None:
    refs = root / "skills" / skill / "references"
    if baseline_root is None:
        node_ids = load_ids(refs / "nodes.jsonl")
        chunk_ids = load_ids(refs / "chunks.jsonl")
        edge_ids = load_ids(refs / "edges.jsonl", edge=True)
        legacy_nodes = [ident for ident in node_ids if not ident.startswith("max-")]
        legacy_chunks = [ident for ident in chunk_ids if not ident.startswith("chunk-max-")]
        legacy_edges = [
            ident
            for ident in edge_ids
            if not any(part.startswith("max-") for part in ident.split("->"))
        ]
        minimums = {
            "backend-architecture": (40, 15, 80),
            "fastapi-clean-architecture": (25, 8, 25),
            "spring-modern-api": (25, 8, 35),
            "python-architecture-patterns": (20, 6, 25),
            "domain-driven-design-first-steps": (25, 8, 25),
            "modern-java-in-action": (20, 8, 20),
            "tidy-first": (20, 6, 25),
            "daily-webnovel-writing-knowledge-skill": (0, 0, 0),
            "teddynote-langchain-rag": (0, 0, 0),
        }
        min_nodes, min_chunks, min_edges = minimums.get(skill, (5, 2, 5))
        if len(legacy_nodes) < min_nodes:
            raise ValueError(f"{skill}: only {len(legacy_nodes)} non-generated node IDs remain")
        if len(legacy_chunks) < min_chunks:
            raise ValueError(f"{skill}: only {len(legacy_chunks)} non-generated chunk IDs remain")
        if len(legacy_edges) < min_edges:
            raise ValueError(f"{skill}: only {len(legacy_edges)} non-generated edge IDs remain")
        return
    base_refs = baseline_root / "skills" / skill / "references"
    for name, edge in [("nodes", False), ("chunks", False), ("edges", True)]:
        before = load_ids(base_refs / f"{name}.jsonl", edge=edge)
        after = load_ids(refs / f"{name}.jsonl", edge=edge)
        missing = sorted(before - after)
        if missing:
            raise ValueError(f"{skill}: deleted {name} IDs: {missing[:10]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--baseline-root")
    args = parser.parse_args()
    try:
        root = Path(args.repo_root)
        baseline = Path(args.baseline_root) if args.baseline_root else None
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            validate_skill(root, skill, baseline)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("ID stability valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
