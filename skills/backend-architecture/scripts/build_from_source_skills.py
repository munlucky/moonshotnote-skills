#!/usr/bin/env python3
"""Validate backend-architecture source skill registry and coverage.

This script is intentionally conservative: it does not concatenate source
graphs into the curated backend-architecture graph. It verifies that the v2
registry can support deterministic synthesis and that every curated source_ref
points at an active public-safe source skill.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def references_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "references"


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    return value.strip('"')


def load_source_registry(path: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    list_key: str | None = None
    nested_key: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- name:"):
            current = {
                "name": parse_scalar(stripped.split(":", 1)[1]),
                "graph_paths": [],
                "domain_tags": [],
                "public_safety": {},
            }
            sources.append(current)
            list_key = None
            nested_key = None
            continue
        if current is None:
            continue
        if stripped in {"graph_paths:", "domain_tags:"}:
            list_key = stripped[:-1]
            nested_key = None
            continue
        if stripped == "public_safety:":
            list_key = None
            nested_key = "public_safety"
            continue
        if stripped.startswith("- ") and list_key:
            current[list_key].append(parse_scalar(stripped[2:]))
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            if nested_key == "public_safety":
                current["public_safety"][key] = parse_scalar(value)
            else:
                current[key] = parse_scalar(value)
                list_key = None

    return sources


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def source_reference_dir(source: dict[str, Any]) -> Path:
    paths = source.get("graph_paths", [])
    if not paths:
        raise ValueError(f"source {source.get('name')}: graph_paths must not be empty")
    return (repo_root() / paths[0]).parent


def validate_source(source: dict[str, Any]) -> dict[str, Any]:
    name = source.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("source entry missing name")
    if source.get("status") != "active":
        return {"name": name, "status": source.get("status"), "active": False}
    if source.get("public_safety", {}).get("public_sanitized") is not True:
        raise ValueError(f"source {name}: public_safety.public_sanitized must be true")
    if source.get("public_safety", {}).get("raw_source_tracked") is not False:
        raise ValueError(f"source {name}: public_safety.raw_source_tracked must be false")

    graph_paths = source.get("graph_paths", [])
    expected_names = {"nodes.jsonl", "edges.jsonl", "chunks.jsonl"}
    if {Path(path).name for path in graph_paths} != expected_names:
        raise ValueError(f"source {name}: graph_paths must include nodes.jsonl, edges.jsonl, chunks.jsonl")
    for rel_path in graph_paths:
        path = repo_root() / rel_path
        if not path.is_file():
            raise ValueError(f"source {name}: missing graph path {rel_path}")

    ref_dir = source_reference_dir(source)
    manifest_path = ref_dir / "graph_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"source {name}: missing graph_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("public_sanitized") is not True:
        raise ValueError(f"source {name}: graph_manifest public_sanitized must be true")
    nodes = load_jsonl(ref_dir / "nodes.jsonl")
    edges = load_jsonl(ref_dir / "edges.jsonl")
    chunks = load_jsonl(ref_dir / "chunks.jsonl")
    manifest_counts = manifest.get("counts", {})
    actual_counts = {"nodes": len(nodes), "edges": len(edges), "chunks": len(chunks)}
    if manifest_counts != actual_counts:
        raise ValueError(f"source {name}: manifest counts mismatch: expected {actual_counts}, got {manifest_counts}")

    source_ids = {row["id"] for row in nodes if "id" in row}
    source_ids.update(row["id"] for row in chunks if "id" in row)
    source_ids.update(f"{row.get('source')}->{row.get('target')}" for row in edges if row.get("source") and row.get("target"))

    return {
        "name": name,
        "status": source.get("status"),
        "role": source.get("role"),
        "adapter_eligible": source.get("adapter_eligible"),
        "domain_tags": source.get("domain_tags", []),
        "counts": actual_counts,
        "source_ids": source_ids,
        "source_paths": graph_paths,
        "active": True,
    }


def iter_source_refs(item: dict[str, Any]) -> list[dict[str, Any]]:
    refs = item.get("source_refs", [])
    if not isinstance(refs, list):
        return []
    return [ref for ref in refs if isinstance(ref, dict)]


def validate_backend_coverage(active_sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    refs = references_dir()
    backend_items = []
    for filename in ["nodes.jsonl", "edges.jsonl", "chunks.jsonl"]:
        backend_items.extend(load_jsonl(refs / filename))

    ref_count = 0
    source_usage: dict[str, int] = {name: 0 for name in active_sources}
    missing_ids: list[str] = []
    for item in backend_items:
        for ref in iter_source_refs(item):
            source_skill = ref.get("source_skill")
            source_id = ref.get("source_id")
            ref_count += 1
            if source_skill not in active_sources:
                raise ValueError(f"backend source_ref uses inactive or unknown source_skill {source_skill!r}")
            source_usage[source_skill] += 1
            if source_id not in active_sources[source_skill]["source_ids"]:
                missing_ids.append(f"{source_skill}:{source_id}")
    if missing_ids:
        sample = ", ".join(missing_ids[:10])
        raise ValueError(f"backend source_refs point to missing source ids: {sample}")

    return {"source_ref_count": ref_count, "source_usage": source_usage}


def manifest_source_skills(validated_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = []
    for source in sorted((item for item in validated_sources if item.get("active")), key=lambda item: item["name"]):
        entries.append({"name": source["name"], "role": source["role"], "source_paths": source["source_paths"]})
    return entries


def build_report() -> dict[str, Any]:
    registry_path = references_dir() / "source_registry.yaml"
    if not registry_path.is_file():
        raise ValueError(f"missing source registry: {registry_path}")
    sources = load_source_registry(registry_path)
    if not sources:
        raise ValueError("source_registry.yaml: no sources found")

    validated = [validate_source(source) for source in sources]
    active_sources = {source["name"]: source for source in validated if source.get("active")}
    coverage = validate_backend_coverage(active_sources)
    return {
        "registry_path": str(registry_path.relative_to(repo_root())).replace("\\", "/"),
        "active_source_count": len(active_sources),
        "source_skills": manifest_source_skills(validated),
        "coverage": coverage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate registry and coverage")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args()
    try:
        report = build_report()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "Source registry valid: "
            f"{report['active_source_count']} active sources, "
            f"{report['coverage']['source_ref_count']} backend source refs"
        )
        for name, count in sorted(report["coverage"]["source_usage"].items()):
            print(f"- {name}: {count} refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
