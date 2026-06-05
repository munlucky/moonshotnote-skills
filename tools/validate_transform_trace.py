#!/usr/bin/env python3
"""Validate public-safe transform_trace fields for source and backend skills."""

from __future__ import annotations

import argparse
import json
import sys
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
ALL_FILES = ["nodes.jsonl", "edges.jsonl", "chunks.jsonl", "coverage_matrix.jsonl", "query_qa.jsonl"]
BACKEND_FILES = ALL_FILES + ["canonical_registry.jsonl", "promotion_records.jsonl"]
SOURCE_TRACE_FIELDS = {
    "source_id",
    "source_chunk_id",
    "line_range",
    "extraction_kind",
    "candidate_id_hash",
    "abstraction_loss",
    "blocked_material_flags",
    "review_status",
}
BACKEND_TRACE_FIELDS = {
    "source_skill",
    "source_id",
    "source_item_kind",
    "extraction_kind",
    "abstraction_loss",
    "blocked_material_flags",
    "review_status",
}


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


def row_ident(row: dict[str, Any], filename: str) -> str:
    if filename == "edges.jsonl":
        return f"{row.get('source')}->{row.get('target')}"
    return str(row.get("id") or f"line-{row.get('_line_no')}")


def validate_trace(trace: dict[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - set(trace))
    if missing:
        raise ValueError(f"{context}: transform_trace missing {missing}")
    if "line_range" in required:
        line_range = trace.get("line_range")
        if not (
            isinstance(line_range, list)
            and len(line_range) == 2
            and all(isinstance(value, int) and value > 0 for value in line_range)
            and line_range[0] <= line_range[1]
        ):
            raise ValueError(f"{context}: invalid transform_trace line_range")
        if len(str(trace.get("candidate_id_hash", ""))) != 16:
            raise ValueError(f"{context}: candidate_id_hash must be a 16 char digest")
    flags = trace.get("blocked_material_flags")
    if not isinstance(flags, list):
        raise ValueError(f"{context}: blocked_material_flags must be a list")
    if trace.get("abstraction_loss") not in {"low", "medium", "high"}:
        raise ValueError(f"{context}: abstraction_loss must be low, medium, or high")


def validate_skill(skill_dir: Path) -> int:
    is_backend = skill_dir.name == "backend-architecture"
    files = BACKEND_FILES if is_backend else ALL_FILES
    required = BACKEND_TRACE_FIELDS if is_backend else SOURCE_TRACE_FIELDS
    checked = 0
    for filename in files:
        path = skill_dir / "references" / filename
        if not path.exists():
            if filename in {"coverage_matrix.jsonl", "query_qa.jsonl", "canonical_registry.jsonl", "promotion_records.jsonl"}:
                continue
            raise ValueError(f"{skill_dir.name}: missing {filename}")
        for row in load_jsonl(path):
            traces = row.get("transform_trace")
            if not isinstance(traces, list) or not traces:
                raise ValueError(f"{skill_dir.name}:{filename}:{row_ident(row, filename)} missing transform_trace")
            for trace in traces:
                validate_trace(trace, required, f"{skill_dir.name}:{filename}:{row_ident(row, filename)}")
                checked += 1
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            checked = validate_skill(Path(args.root) / skill)
            print(f"{skill}: {checked} transform_trace entries valid")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
