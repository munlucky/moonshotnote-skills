#!/usr/bin/env python3
"""Validate backend meta-skill canonical registry and promotion records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
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


def collect_ids(repo_root: Path, skill: str) -> set[str]:
    refs = repo_root / "skills" / skill / "references"
    ids: set[str] = set()
    for row in load_jsonl(refs / "nodes.jsonl"):
        ids.add(row["id"])
    for row in load_jsonl(refs / "chunks.jsonl"):
        ids.add(row["id"])
    for row in load_jsonl(refs / "edges.jsonl"):
        ids.add(f"{row.get('source')}->{row.get('target')}")
    return ids


def source_registry_names(path: Path) -> list[str]:
    names: list[str] = []
    current_name: str | None = None
    current_status: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            if current_name and current_status == "active":
                names.append(current_name)
            current_name = stripped.split(":", 1)[1].strip().strip('"')
            current_status = None
        elif current_name and stripped.startswith("status:"):
            current_status = stripped.split(":", 1)[1].strip().strip('"')
    if current_name and current_status == "active":
        names.append(current_name)
    if not names:
        raise ValueError(f"{path}: no active source skills found")
    return names


def validate(repo_root: Path) -> None:
    backend_refs = repo_root / "skills" / "backend-architecture" / "references"
    source_registry = source_registry_names(backend_refs / "source_registry.yaml")
    known = {skill: collect_ids(repo_root, skill) for skill in source_registry}
    known["backend-architecture"] = collect_ids(repo_root, "backend-architecture")

    for row in load_jsonl(backend_refs / "canonical_registry.jsonl"):
        for member in row.get("members", []):
            if ":" not in member:
                raise ValueError(f"canonical_registry:{row['_line_no']}: invalid member {member!r}")
            skill, ident = member.split(":", 1)
            if skill not in known or ident not in known[skill]:
                raise ValueError(f"canonical_registry:{row['_line_no']}: unknown member {member}")
        for ref in row.get("source_refs", []):
            skill = ref.get("source_skill")
            ident = ref.get("source_id")
            if skill not in known or ident not in known[skill]:
                raise ValueError(f"canonical_registry:{row['_line_no']}: unknown source_ref {skill}:{ident}")

    for row in load_jsonl(backend_refs / "promotion_records.jsonl"):
        evidence = row.get("source_evidence", [])
        if not evidence:
            raise ValueError(f"promotion_records:{row['_line_no']}: source_evidence required")
        sources = set()
        for ref in evidence:
            skill = ref.get("source_skill")
            ident = ref.get("source_id")
            if skill not in known or ident not in known[skill]:
                raise ValueError(f"promotion_records:{row['_line_no']}: unknown evidence {skill}:{ident}")
            sources.add(skill)
        if row.get("independent_source_count") != len(sources):
            raise ValueError(
                f"promotion_records:{row['_line_no']}: independent_source_count "
                f"{row.get('independent_source_count')} != {len(sources)}"
            )
        if row.get("node_id") not in known["backend-architecture"]:
            raise ValueError(f"promotion_records:{row['_line_no']}: unknown backend node {row.get('node_id')}")
        if row.get("public_safe") is not True:
            raise ValueError(f"promotion_records:{row['_line_no']}: public_safe must be true")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    try:
        validate(Path(args.repo_root))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Backend meta artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
