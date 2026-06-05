#!/usr/bin/env python3
"""Fail if OCR graph artifacts lack chunk-text extraction evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SOURCE_SKILLS = {
    "tidy-first",
    "fastapi-clean-architecture",
    "modern-java-in-action",
    "domain-driven-design-first-steps",
    "spring-modern-api",
    "python-architecture-patterns",
}


def validate_skill(skill_dir: Path, run_id: str) -> tuple[int, int]:
    manifest_path = skill_dir / "references" / "graph_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    extraction = manifest.get("chunk_grounded_extraction")
    if not extraction:
        raise ValueError(f"{skill_dir.name}: graph_manifest.json lacks chunk_grounded_extraction")
    if skill_dir.name in SOURCE_SKILLS:
        if extraction.get("status") != "trace_attached":
            raise ValueError(f"{skill_dir.name}: expected trace_attached extraction status")
        if extraction.get("run_id") != run_id:
            raise ValueError(f"{skill_dir.name}: extraction run_id mismatch")
        triaged = int(extraction.get("source_chunks_triaged") or 0)
        accepted = int(extraction.get("accepted_semantic_candidates") or 0)
        if triaged <= 0 or accepted <= 0:
            raise ValueError(f"{skill_dir.name}: invalid triaged/accepted candidate counts")
        ledger = skill_dir / "output" / "extraction-candidates" / run_id / "semantic_candidates.jsonl"
        if not ledger.is_file():
            raise ValueError(f"{skill_dir.name}: missing private extraction ledger {ledger}")
        return triaged, accepted
    if skill_dir.name == "backend-architecture":
        if extraction.get("status") != "source_graph_trace_attached":
            raise ValueError("backend-architecture: expected source_graph_trace_attached status")
        return 0, 0
    return 0, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            triaged, accepted = validate_skill(Path(args.root) / skill, args.run_id)
            if triaged:
                print(f"{skill}: chunk-grounded extraction present ({accepted}/{triaged} accepted)")
            else:
                print(f"{skill}: source-public graph extraction present")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
