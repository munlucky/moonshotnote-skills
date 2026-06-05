#!/usr/bin/env python3
"""Validate that public source-skill rows are grounded in private chunk candidates."""

from __future__ import annotations

import argparse
import hashlib
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
    "daily-webnovel-writing-knowledge-skill",
    "teddynote-langchain-rag",
}
PUBLIC_FILES = ["nodes.jsonl", "edges.jsonl", "chunks.jsonl", "coverage_matrix.jsonl", "query_qa.jsonl"]
BLOCKING_FLAGS = {"code_heavy", "table_heavy", "exercise_or_qa", "toc_or_index"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def candidate_hash(candidate_id: str) -> str:
    return hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16]


def load_candidate_index(skill_dir: Path, run_id: str) -> dict[str, dict[str, Any]]:
    path = skill_dir / "output" / "extraction-candidates" / run_id / "semantic_candidates.jsonl"
    if not path.is_file():
        raise ValueError(f"{skill_dir.name}: missing private candidate ledger {path}")
    index: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        index[candidate_hash(row["candidate_id"])] = row
    if not index:
        raise ValueError(f"{skill_dir.name}: empty private candidate ledger")
    return index


def row_line_ranges(row: dict[str, Any]) -> list[list[int]]:
    ranges: list[list[int]] = []
    for ref in row.get("source_refs") or []:
        candidate = ref.get("line_range") or ref.get("lines")
        if isinstance(candidate, list) and len(candidate) == 2:
            ranges.append([int(candidate[0]), int(candidate[1])])
    if isinstance(row.get("line_range"), list) and len(row["line_range"]) == 2:
        ranges.append([int(row["line_range"][0]), int(row["line_range"][1])])
    return ranges


def overlaps(left: list[int], right: list[int]) -> bool:
    return max(left[0], right[0]) <= min(left[1], right[1])


def ident(row: dict[str, Any], filename: str) -> str:
    if filename == "edges.jsonl":
        return f"{row.get('source')}->{row.get('target')}"
    return str(row.get("id") or f"line-{row.get('_line_no')}")


def validate_skill(skill_dir: Path, run_id: str) -> tuple[int, int]:
    candidate_index = load_candidate_index(skill_dir, run_id)
    checked = 0
    for filename in PUBLIC_FILES:
        path = skill_dir / "references" / filename
        if not path.is_file():
            if filename == "query_qa.jsonl":
                continue
            raise ValueError(f"{skill_dir.name}: missing {filename}")
        for row in load_jsonl(path):
            traces = row.get("transform_trace")
            if not isinstance(traces, list) or not traces:
                raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} missing transform_trace")
            ranges = row_line_ranges(row)
            for trace in traces:
                cand_hash = trace.get("candidate_id_hash")
                if cand_hash not in candidate_index:
                    raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} unknown candidate hash {cand_hash}")
                candidate = candidate_index[cand_hash]
                if candidate.get("accepted_for_public_graph") is not True:
                    raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} uses rejected candidate")
                flags = set(candidate.get("blocked_material_flags") or [])
                if flags & BLOCKING_FLAGS:
                    raise ValueError(
                        f"{skill_dir.name}:{filename}:{ident(row, filename)} uses blocked candidate flags {sorted(flags & BLOCKING_FLAGS)}"
                    )
                if trace.get("source_chunk_id") != candidate.get("source_chunk_id"):
                    raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} source_chunk_id mismatch")
                if filename != "query_qa.jsonl":
                    if not ranges:
                        raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} missing source line range")
                    trace_range = trace.get("line_range")
                    if not any(overlaps(line_range, trace_range) for line_range in ranges):
                        raise ValueError(
                            f"{skill_dir.name}:{filename}:{ident(row, filename)} transform_trace does not overlap source_refs"
                        )
                checked += 1
    accepted = sum(1 for row in candidate_index.values() if row.get("accepted_for_public_graph") is True)
    return checked, accepted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            if skill not in SOURCE_SKILLS:
                continue
            checked, accepted = validate_skill(Path(args.root) / skill, args.run_id)
            print(f"{skill}: {checked} public traces grounded in {accepted} accepted candidates")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
