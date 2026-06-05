#!/usr/bin/env python3
"""Attach public-safe transform traces derived from private chunk candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_SKILLS = [
    "tidy-first",
    "fastapi-clean-architecture",
    "modern-java-in-action",
    "domain-driven-design-first-steps",
    "spring-modern-api",
    "python-architecture-patterns",
]
BACKEND_SKILL = "backend-architecture"
SOURCE_IDS = {
    "tidy-first": "tidy-first-ocr",
    "fastapi-clean-architecture": "fastapi-clean-architecture-reviewed-ocr",
    "modern-java-in-action": "modern-java-in-action-reviewed-ocr",
    "domain-driven-design-first-steps": "domain-driven-design-first-steps-ocr",
    "spring-modern-api": "spring-modern-api-reviewed-ocr",
    "python-architecture-patterns": "python-architecture-patterns-reviewed-ocr",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def overlap(a: list[int] | None, b: list[int] | None) -> int:
    if not a or not b:
        return 0
    start = max(int(a[0]), int(b[0]))
    end = min(int(a[1]), int(b[1]))
    return max(0, end - start + 1)


def candidate_hash(candidate_id: str) -> str:
    return hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16]


def load_candidates(repo: Path, skill: str, run_id: str) -> list[dict[str, Any]]:
    path = repo / "skills" / skill / "output" / "extraction-candidates" / run_id / "semantic_candidates.jsonl"
    rows = load_jsonl(path)
    if not rows:
        raise ValueError(f"{skill}: missing private candidate ledger: {path}")
    return rows


def source_line_ranges(row: dict[str, Any]) -> list[list[int]]:
    ranges: list[list[int]] = []
    for ref in row.get("source_refs") or []:
        candidate = ref.get("line_range") or ref.get("lines")
        if isinstance(candidate, list) and len(candidate) == 2:
            ranges.append([int(candidate[0]), int(candidate[1])])
    if "line_range" in row and isinstance(row["line_range"], list) and len(row["line_range"]) == 2:
        ranges.append([int(row["line_range"][0]), int(row["line_range"][1])])
    return ranges


def select_candidate(row: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    ranges = source_line_ranges(row)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for cand in candidates:
        score = max((overlap(line_range, cand.get("line_range")) for line_range in ranges), default=0)
        accepted = 1 if cand.get("accepted_for_public_graph") is True else 0
        if score:
            scored.append((score, accepted, cand))
    accepted_scored = [item for item in scored if item[1] == 1]
    if not ranges:
        raise ValueError(f"row has no source line range for chunk grounding: {row.get('id') or row.get('source')}")
    if not accepted_scored:
        raise ValueError(
            f"no accepted overlapping chunk candidate for row {row.get('id') or row.get('source')} ranges={ranges[:3]}"
        )
    accepted_scored.sort(key=lambda item: (-item[0], item[2].get("source_chunk_id", "")))
    return accepted_scored[0][2]


def source_trace(cand: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": cand["source_id"],
        "source_chunk_id": cand["source_chunk_id"],
        "line_range": cand["line_range"],
        "extraction_kind": cand["extraction_kind"],
        "candidate_id_hash": candidate_hash(cand["candidate_id"]),
        "abstraction_loss": cand["abstraction_loss"],
        "blocked_material_flags": cand.get("blocked_material_flags", []),
        "review_status": cand["review_status"],
    }


def apply_source_skill(repo: Path, skill: str, run_id: str) -> None:
    refs = repo / "skills" / skill / "references"
    candidates = load_candidates(repo, skill, run_id)
    for filename in ["nodes.jsonl", "edges.jsonl", "chunks.jsonl", "coverage_matrix.jsonl"]:
        rows = load_jsonl(refs / filename)
        for row in rows:
            trace = source_trace(select_candidate(row, candidates))
            row["transform_trace"] = [trace]
            if filename == "coverage_matrix.jsonl":
                chunk_id = trace["source_chunk_id"]
                row["source_chunk_ids"] = [chunk_id]
                if row.get("coverage_status") != "gap":
                    row["coverage_status"] = "covered" if row.get("market_substitute_risk") == "low" else row["coverage_status"]
        write_jsonl(refs / filename, rows)

    nodes = {row["id"]: row.get("transform_trace", []) for row in load_jsonl(refs / "nodes.jsonl")}
    chunks = {row["id"]: row.get("transform_trace", []) for row in load_jsonl(refs / "chunks.jsonl")}
    qa_path = refs / "query_qa.jsonl"
    qa_rows = load_jsonl(qa_path)
    for row in qa_rows:
        traces: list[dict[str, Any]] = []
        for ident in row.get("expected_nodes", [])[:2]:
            traces.extend(nodes.get(ident, [])[:1])
        for ident in row.get("expected_chunks", [])[:2]:
            traces.extend(chunks.get(ident, [])[:1])
        row["transform_trace"] = traces[:3] or [source_trace(next(c for c in candidates if c.get("accepted_for_public_graph")))]
    if qa_rows:
        write_jsonl(qa_path, qa_rows)

    manifest_path = refs / "graph_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    accepted = sum(1 for cand in candidates if cand.get("accepted_for_public_graph") is True)
    manifest["chunk_grounded_extraction"] = {
        "status": "trace_attached",
        "run_id": run_id,
        "source_chunks_triaged": len(candidates),
        "accepted_semantic_candidates": accepted,
        "source_id": SOURCE_IDS[skill],
        "public_trace_policy": "public rows store stable chunk references, line ranges, short candidate digests, and abstraction loss labels only. OCR text is excluded",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{skill}: transform_trace attached from {accepted}/{len(candidates)} accepted candidates")


def normalize_backend_ref(ref: Any) -> dict[str, Any]:
    if isinstance(ref, dict):
        return ref
    if isinstance(ref, str) and ":" in ref:
        source_skill, source_id = ref.split(":", 1)
        return {"source_skill": source_skill, "source_id": source_id, "source_item_kind": "node"}
    return {}


def backend_trace_from_ref(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_skill": ref.get("source_skill"),
        "source_id": ref.get("source_id"),
        "source_item_kind": ref.get("source_item_kind", "unknown"),
        "extraction_kind": "public_graph_promotion",
        "abstraction_loss": "high",
        "blocked_material_flags": [],
        "review_status": "source_public_graph_only",
    }


def apply_backend(repo: Path) -> None:
    refs = repo / "skills" / BACKEND_SKILL / "references"
    for filename in ["nodes.jsonl", "edges.jsonl", "chunks.jsonl", "query_qa.jsonl", "canonical_registry.jsonl", "promotion_records.jsonl"]:
        path = refs / filename
        rows = load_jsonl(path)
        if not rows:
            continue
        for row in rows:
            trace_refs: list[dict[str, Any]] = []
            if filename == "promotion_records.jsonl":
                trace_refs = row.get("source_evidence", []) or []
            elif filename == "canonical_registry.jsonl":
                trace_refs = row.get("members", []) or []
            else:
                trace_refs = row.get("source_refs", []) or []
            normalized_refs = [normalize_backend_ref(ref) for ref in trace_refs[:4]]
            row["transform_trace"] = [
                backend_trace_from_ref(ref) for ref in normalized_refs if ref.get("source_skill") and ref.get("source_id")
            ]
            if not row["transform_trace"] and row.get("expected_source_skills"):
                row["transform_trace"] = [
                    {
                        "source_skill": row["expected_source_skills"][0],
                        "source_id": "query-fixture-public-graph",
                        "source_item_kind": "query",
                        "extraction_kind": "public_graph_retrieval_check",
                        "abstraction_loss": "high",
                        "blocked_material_flags": [],
                        "review_status": "source_public_graph_only",
                    }
                ]
        write_jsonl(path, rows)
    manifest_path = refs / "graph_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["chunk_grounded_extraction"] = {
        "status": "source_graph_trace_attached",
        "public_trace_policy": "backend uses source skill public graph IDs only; no raw OCR or private chunk access",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("backend-architecture: source public graph transform_trace attached")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()
    repo = Path(args.repo_root)
    for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
        if skill in SOURCE_SKILLS:
            apply_source_skill(repo, skill, args.run_id)
        elif skill == BACKEND_SKILL:
            apply_backend(repo)
        else:
            raise SystemExit(f"unsupported skill: {skill}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
