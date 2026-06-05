#!/usr/bin/env python3
"""Validate public-safe coverage matrices for OCR-derived source skills."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "source_id",
    "chapter",
    "section",
    "line_range",
    "ocr_review_status",
    "chunk_ids",
    "node_ids",
    "edge_ids",
    "coverage_status",
    "gap_reason",
    "market_substitute_risk",
    "heart_of_work_risk",
}
ALLOWED_COVERAGE = {"covered", "limited", "gap"}
ALLOWED_RISK = {"low", "medium"}


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        row["_line_no"] = line_no
        rows.append(row)
    return rows


def row_ids(path: Path, edge: bool = False) -> set[str]:
    ids: set[str] = set()
    for row in load_jsonl(path):
        if edge:
            ids.add(f"{row.get('source')}->{row.get('target')}")
        else:
            ids.add(row["id"])
    return ids


def validate_skill(skill_dir: Path, min_coverage: float) -> tuple[int, int]:
    refs = skill_dir / "references"
    matrix_path = refs / "coverage_matrix.jsonl"
    if not matrix_path.is_file():
        raise ValueError(f"{skill_dir.name}: missing coverage_matrix.jsonl")
    node_ids = row_ids(refs / "nodes.jsonl")
    edge_ids = row_ids(refs / "edges.jsonl", edge=True)
    chunk_ids = row_ids(refs / "chunks.jsonl")
    rows = load_jsonl(matrix_path)
    if not rows:
        raise ValueError(f"{skill_dir.name}: coverage_matrix.jsonl must not be empty")

    covered = 0
    for row in rows:
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: missing fields {missing}")
        line_range = row["line_range"]
        if not (
            isinstance(line_range, list)
            and len(line_range) == 2
            and all(isinstance(value, int) and value > 0 for value in line_range)
            and line_range[0] <= line_range[1]
        ):
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: line_range must be [start, end]")
        if row["coverage_status"] not in ALLOWED_COVERAGE:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: invalid coverage_status")
        if row["market_substitute_risk"] not in ALLOWED_RISK:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: invalid market_substitute_risk")
        if row["heart_of_work_risk"] not in ALLOWED_RISK:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: invalid heart_of_work_risk")
        if row["coverage_status"] == "gap" and not row["gap_reason"]:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: gap rows require gap_reason")
        if row["coverage_status"] != "gap":
            covered += 1
            for ident in row["node_ids"]:
                if ident not in node_ids:
                    raise ValueError(f"{skill_dir.name}:{row['_line_no']}: unknown node_id {ident}")
            for ident in row["edge_ids"]:
                if ident not in edge_ids:
                    raise ValueError(f"{skill_dir.name}:{row['_line_no']}: unknown edge_id {ident}")
            for ident in row["chunk_ids"]:
                if ident not in chunk_ids:
                    raise ValueError(f"{skill_dir.name}:{row['_line_no']}: unknown chunk_id {ident}")

    ratio = covered / len(rows)
    if ratio < min_coverage:
        raise ValueError(f"{skill_dir.name}: coverage {ratio:.2%} below required {min_coverage:.2%}")
    return covered, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    parser.add_argument("--min-coverage", type=float, default=0.9)
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            covered, total = validate_skill(Path(args.root) / skill, args.min_coverage)
            print(f"{skill}: coverage {covered}/{total}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
