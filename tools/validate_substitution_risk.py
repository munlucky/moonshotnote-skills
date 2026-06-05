#!/usr/bin/env python3
"""Validate that public graph artifacts do not become a source-text substitute."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_SKILLS = {
    "tidy-first",
    "fastapi-clean-architecture",
    "modern-java-in-action",
    "domain-driven-design-first-steps",
    "spring-modern-api",
    "python-architecture-patterns",
}
FILES = ["nodes.jsonl", "edges.jsonl", "chunks.jsonl", "coverage_matrix.jsonl", "query_qa.jsonl"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def validate_source_skill(skill_dir: Path) -> tuple[int, int]:
    chunk_use: Counter[str] = Counter()
    summary_chars = 0
    public_rows = 0
    medium_risk = 0
    for filename in FILES:
        for row in load_jsonl(skill_dir / "references" / filename):
            public_rows += 1
            for key in ["summary", "question", "pass_criteria"]:
                value = row.get(key)
                if isinstance(value, str):
                    summary_chars += len(value)
            for trace in row.get("transform_trace") or []:
                chunk_id = trace.get("source_chunk_id")
                if chunk_id:
                    chunk_use[str(chunk_id)] += 1
            if row.get("market_substitute_risk") == "medium" or row.get("heart_of_work_risk") == "medium":
                medium_risk += 1
    if not chunk_use:
        raise ValueError(f"{skill_dir.name}: no source_chunk_id usage in transform_trace")
    total_trace_refs = sum(chunk_use.values())
    dominant_ratio = max(chunk_use.values()) / total_trace_refs
    max_dominant_ratio = 0.25 if len(chunk_use) < 30 else 0.18
    if dominant_ratio > max_dominant_ratio:
        raise ValueError(f"{skill_dir.name}: too much public graph depends on one source chunk ({dominant_ratio:.1%})")
    if public_rows and summary_chars / public_rows > 520:
        raise ValueError(f"{skill_dir.name}: average public explanatory text is too long")
    return public_rows, medium_risk


def validate_backend(skill_dir: Path) -> int:
    rows = 0
    for filename in ["nodes.jsonl", "edges.jsonl", "chunks.jsonl", "query_qa.jsonl", "canonical_registry.jsonl", "promotion_records.jsonl"]:
        for row in load_jsonl(skill_dir / "references" / filename):
            rows += 1
            for trace in row.get("transform_trace") or []:
                if "source_chunk_id" in trace:
                    raise ValueError(f"{skill_dir.name}:{filename}: backend transform_trace must not reference private chunks")
                if trace.get("extraction_kind") not in {"public_graph_promotion", "public_graph_retrieval_check"}:
                    raise ValueError(f"{skill_dir.name}:{filename}: backend trace must be source-public-graph only")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            skill_dir = Path(args.root) / skill
            if skill in SOURCE_SKILLS:
                rows, medium = validate_source_skill(skill_dir)
                print(f"{skill}: substitution-risk shape ok ({rows} rows, {medium} medium-risk rows)")
            elif skill == "backend-architecture":
                rows = validate_backend(skill_dir)
                print(f"{skill}: backend source-public trace only ({rows} rows)")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
