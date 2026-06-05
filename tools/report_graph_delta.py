#!/usr/bin/env python3
"""Report public graph counts and density against optional baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FILES = ["nodes", "edges", "chunks", "coverage_matrix", "query_qa", "canonical_registry", "promotion_records"]


def count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def snapshot(root: Path, skills: list[str]) -> dict[str, dict[str, int]]:
    data: dict[str, dict[str, int]] = {}
    for skill in skills:
        refs = root / "skills" / skill / "references"
        data[skill] = {name: count(refs / f"{name}.jsonl") for name in FILES}
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--baseline-json")
    parser.add_argument("--write-baseline")
    args = parser.parse_args()

    skills = [item.strip() for item in args.skills.split(",") if item.strip()]
    data = snapshot(Path(args.repo_root), skills)
    if args.write_baseline:
        Path(args.write_baseline).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    baseline = {}
    if args.baseline_json:
        baseline = json.loads(Path(args.baseline_json).read_text(encoding="utf-8"))

    for skill, counts in data.items():
        nodes = counts["nodes"]
        edges = counts["edges"]
        chunks = counts["chunks"]
        edge_density = edges / nodes if nodes else 0
        node_density = nodes / chunks if chunks else 0
        print(f"{skill}: nodes={nodes} edges={edges} chunks={chunks} e/n={edge_density:.2f} n/ch={node_density:.2f}")
        if skill in baseline:
            deltas = {key: counts[key] - baseline[skill].get(key, 0) for key in FILES}
            print("  delta: " + " ".join(f"{key}={value:+d}" for key, value in deltas.items() if value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
