#!/usr/bin/env python3
"""Validate generated edge and backend mapping evidence is not synthetic."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SOURCE_EDGE_RULE = "same_section_or_curated_topic_relation"
BACKEND_EDGE_RULE = "public_source_graph_promotion"


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ref_key(ref: dict, backend: bool = False) -> tuple:
    if backend:
        return (ref.get("source_skill"), ref.get("source_id"))
    return (ref.get("source_id"), ref.get("chapter"), tuple(ref.get("line_range") or ref.get("lines") or []))


def terms(text: str) -> set[str]:
    stop = {"boundary", "decision", "warning", "contract", "pattern", "concept", "backend", "architecture", "public", "safe"}
    return {term for term in re.findall(r"[a-z0-9가-힣]+", text.lower()) if len(term) > 2 and term not in stop}


def row_text(row: dict) -> str:
    values = [str(row.get("id", "")), str(row.get("name", "")), str(row.get("title", "")), str(row.get("summary", ""))]
    for key in ("aliases", "keywords"):
        if isinstance(row.get(key), list):
            values.extend(str(item) for item in row[key])
    return " ".join(values)


def collect_source_rows(repo: Path) -> dict[str, dict[str, dict]]:
    skills_dir = repo / "skills"
    result: dict[str, dict[str, dict]] = {}
    for refs in skills_dir.glob("*/references"):
        skill = refs.parent.name
        rows: dict[str, dict] = {}
        for row in load_jsonl(refs / "nodes.jsonl"):
            rows[row["id"]] = row
        for row in load_jsonl(refs / "chunks.jsonl"):
            rows[row["id"]] = row
        for row in load_jsonl(refs / "edges.jsonl"):
            rows[f"{row.get('source')}->{row.get('target')}"] = row
        result[skill] = rows
    return result


def validate_source_skill(repo: Path, skill: str) -> None:
    refs = repo / "skills" / skill / "references"
    nodes = {row["id"]: row for row in load_jsonl(refs / "nodes.jsonl")}
    for line_no, edge in enumerate(load_jsonl(refs / "edges.jsonl"), start=1):
        if edge.get("evidence_rule") != SOURCE_EDGE_RULE:
            continue
        source = nodes[edge["source"]]
        target = nodes[edge["target"]]
        edge_refs = {ref_key(ref) for ref in edge.get("source_refs", [])}
        source_refs = {ref_key(ref) for ref in source.get("source_refs", [])}
        target_refs = {ref_key(ref) for ref in target.get("source_refs", [])}
        if not edge_refs or not (edge_refs & source_refs & target_refs):
            raise ValueError(f"{skill}: edge line {line_no} lacks shared source/target evidence")


def validate_backend(repo: Path) -> None:
    refs = repo / "skills" / "backend-architecture" / "references"
    all_rows = collect_source_rows(repo)
    backend_nodes = {row["id"]: row for row in load_jsonl(refs / "nodes.jsonl")}
    for line_no, edge in enumerate(load_jsonl(refs / "edges.jsonl"), start=1):
        if edge.get("evidence_rule") != BACKEND_EDGE_RULE:
            continue
        edge_refs = {ref_key(ref, backend=True) for ref in edge.get("source_refs", [])}
        source_refs = {ref_key(ref, backend=True) for ref in backend_nodes[edge["source"]].get("source_refs", [])}
        target_refs = {ref_key(ref, backend=True) for ref in backend_nodes[edge["target"]].get("source_refs", [])}
        if len({skill for skill, _ in edge_refs if skill}) < 2:
            raise ValueError(f"backend edge line {line_no}: needs at least two source skills")
        if not (edge_refs & source_refs) or not (edge_refs & target_refs):
            raise ValueError(f"backend edge line {line_no}: must include source and target node evidence")

    for line_no, row in enumerate(load_jsonl(refs / "canonical_registry.jsonl"), start=1):
        if not row.get("id", "").startswith("canonical-max-"):
            continue
        label_terms = terms(str(row.get("label", "")))
        if not label_terms:
            raise ValueError(f"canonical_registry line {line_no}: label lacks searchable terms")
        matched = 0
        for member in row.get("members", []):
            skill, ident = member.split(":", 1)
            member_row = all_rows.get(skill, {}).get(ident)
            if member_row and label_terms & terms(row_text(member_row)):
                matched += 1
        if matched == 0:
            raise ValueError(f"canonical_registry line {line_no}: no member semantically matches label")

    for line_no, row in enumerate(load_jsonl(refs / "promotion_records.jsonl"), start=1):
        if not row.get("id", "").startswith("promotion-max-"):
            continue
        evidence = row.get("source_evidence", [])
        if len({item.get("source_skill") for item in evidence}) < 2:
            raise ValueError(f"promotion_records line {line_no}: needs at least two independent source skills")
        if not row.get("limitations") or len(row["limitations"]) < 20:
            raise ValueError(f"promotion_records line {line_no}: limitations must be specific")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    try:
        repo = Path(args.repo_root)
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            if skill == "backend-architecture":
                validate_backend(repo)
            else:
                validate_source_skill(repo, skill)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Edge evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
