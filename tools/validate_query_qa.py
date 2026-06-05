#!/usr/bin/env python3
"""Validate query QA fixtures for public-safe knowledge graph skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "id",
    "question",
    "expected_nodes",
    "expected_chunks",
    "expected_source_skills",
    "min_hit_count",
    "pass_criteria",
    "public_safe",
}


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


def ids(path: Path) -> set[str]:
    return {row["id"] for row in load_jsonl(path)}


def terms(text: str) -> list[str]:
    raw = [item.lower() for item in re.findall(r"[A-Za-z0-9가-힣_]+(?:-[A-Za-z0-9_]+)*", text)]
    for hyphenated in list(raw):
        raw.extend(part for part in hyphenated.split("-") if part)
    stop = {"the", "and", "or", "with", "public", "safe", "어떤", "함께", "봐야", "하나", "기준", "적용"}
    return [item for item in raw if len(item) > 1 and item not in stop]


def searchable_text(row: dict) -> str:
    values = []
    for key, value in row.items():
        if key in {"source_refs", "public_safe"} or key.startswith("_"):
            continue
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
    return " ".join(values).lower()


def ranked_ids(rows: list[dict], question: str, limit: int) -> list[str]:
    query_terms = terms(question)
    question_lower = question.lower()
    scored = []
    for row in rows:
        haystack = searchable_text(row)
        score = sum(1 for term in query_terms if term in haystack)
        natural_labels = [str(row.get("name") or row.get("title") or "")]
        if isinstance(row.get("aliases"), list):
            natural_labels.extend(str(item) for item in row["aliases"])
        if isinstance(row.get("keywords"), list):
            natural_labels.extend(str(item) for item in row["keywords"])
        for label in natural_labels:
            label_lower = label.lower().strip()
            if label_lower and label_lower in question_lower:
                score += 25
        if score:
            scored.append((score, row["id"]))
    return [ident for _, ident in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]]


def expected_is_lexically_supported(question: str, rows_by_id: dict[str, dict], expected: list[str]) -> bool:
    query_terms = set(terms(question))
    for ident in expected:
        row = rows_by_id[ident]
        candidate_terms = set(terms(str(row.get("name") or row.get("title") or "")))
        for value in row.get("aliases", []) if isinstance(row.get("aliases"), list) else []:
            candidate_terms.update(terms(str(value)))
        for value in row.get("keywords", []) if isinstance(row.get("keywords"), list) else []:
            candidate_terms.update(terms(str(value)))
        if not (query_terms & candidate_terms):
            return False
    return True


def validate_skill(skill_dir: Path, top_n: int) -> int:
    refs = skill_dir / "references"
    qa_path = refs / "query_qa.jsonl"
    if not qa_path.is_file():
        raise ValueError(f"{skill_dir.name}: missing query_qa.jsonl")
    rows = load_jsonl(qa_path)
    min_rows = 40 if skill_dir.name == "backend-architecture" else 30
    if len(rows) < min_rows:
        raise ValueError(f"{skill_dir.name}: expected at least {min_rows} query QA rows, got {len(rows)}")
    node_rows = load_jsonl(refs / "nodes.jsonl")
    chunk_rows = load_jsonl(refs / "chunks.jsonl")
    node_ids = {row["id"] for row in node_rows}
    chunk_ids = {row["id"] for row in chunk_rows}
    node_by_id = {row["id"]: row for row in node_rows}
    chunk_by_id = {row["id"]: row for row in chunk_rows}
    for row in rows:
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: missing fields {missing}")
        if row.get("public_safe") is not True:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: public_safe must be true")
        if not isinstance(row["expected_nodes"], list) or not row["expected_nodes"]:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: expected_nodes must be non-empty")
        if not isinstance(row["expected_chunks"], list) or not row["expected_chunks"]:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: expected_chunks must be non-empty")
        if not isinstance(row["expected_source_skills"], list) or not row["expected_source_skills"]:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: expected_source_skills must be non-empty")
        if not isinstance(row["min_hit_count"], int) or row["min_hit_count"] <= 0:
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: min_hit_count must be positive")
        for ident in row["expected_nodes"]:
            if ident not in node_ids:
                raise ValueError(f"{skill_dir.name}:{row['_line_no']}: unknown expected node {ident}")
        for ident in row["expected_chunks"]:
            if ident not in chunk_ids:
                raise ValueError(f"{skill_dir.name}:{row['_line_no']}: unknown expected chunk {ident}")
        if not expected_is_lexically_supported(row["question"], node_by_id, row["expected_nodes"]):
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: question does not naturally reference expected node terms")
        if not expected_is_lexically_supported(row["question"], chunk_by_id, row["expected_chunks"]):
            raise ValueError(f"{skill_dir.name}:{row['_line_no']}: question does not naturally reference expected chunk terms")
        ranked_nodes = set(ranked_ids(node_rows, row["question"], top_n))
        ranked_chunks = set(ranked_ids(chunk_rows, row["question"], top_n))
        missing_nodes = [ident for ident in row["expected_nodes"] if ident not in ranked_nodes]
        missing_chunks = [ident for ident in row["expected_chunks"] if ident not in ranked_chunks]
        if missing_nodes or missing_chunks:
            raise ValueError(
                f"{skill_dir.name}:{row['_line_no']}: expected hits missing from top {top_n}: "
                f"nodes={missing_nodes}, chunks={missing_chunks}"
            )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            count = validate_skill(Path(args.root) / skill, args.top_n)
            print(f"{skill}: query QA rows {count}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
