#!/usr/bin/env python3
"""Validate the public-safe backend architecture graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_NODE_FIELDS = {"id", "type", "name", "summary", "aliases", "source_refs", "public_safe"}
REQUIRED_EDGE_FIELDS = {"source", "target", "type", "summary", "source_refs", "public_safe"}
REQUIRED_CHUNK_FIELDS = {"id", "title", "summary", "source_refs", "keywords", "public_safe"}
NODE_TYPES = {"Principle", "Layer", "Boundary", "Pattern", "Workflow", "Tradeoff", "FrameworkAdapter", "Warning"}
EDGE_TYPES = {
    "belongs_to",
    "governs",
    "implements",
    "depends_inward",
    "implements_abstraction",
    "separates_from",
    "supports",
    "operationalizes",
    "reduces",
    "increases",
    "trades_off_with",
    "warns_about",
    "maps_to",
    "includes",
    "next_topic",
}
SOURCE_SKILLS = {
    "fastapi-clean-architecture",
    "tidy-first",
    "spring-modern-api",
    "python-architecture-patterns",
    "domain-driven-design-first-steps",
}
RAW_TEXT_RISK_PATTERNS = [
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"/Users/"),
    re.compile(r"\bocr-output\b", re.IGNORECASE),
    re.compile(r"\bprivate-source\b", re.IGNORECASE),
]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def require_fields(kind: str, item: dict, required: set[str]) -> None:
    missing = sorted(required - set(item))
    if missing:
        raise ValueError(f"{kind} {item.get('id') or item.get('source')}: missing fields: {missing}")


def validate_source_refs(kind: str, ident: str, refs: object) -> None:
    if not isinstance(refs, list) or not refs:
        raise ValueError(f"{kind} {ident}: source_refs must be a non-empty list")
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError(f"{kind} {ident}: source_ref must be an object")
        source_skill = ref.get("source_skill")
        source_id = ref.get("source_id")
        if source_skill not in SOURCE_SKILLS:
            raise ValueError(f"{kind} {ident}: invalid source_skill {source_skill!r}")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(f"{kind} {ident}: source_id must be a non-empty string")


def validate_public_text(kind: str, ident: str, item: dict, max_summary_chars: int) -> None:
    if item.get("public_safe") is not True:
        raise ValueError(f"{kind} {ident}: public_safe must be true")
    summary = item.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError(f"{kind} {ident}: summary must be a non-empty string")
    if len(summary) > max_summary_chars:
        raise ValueError(f"{kind} {ident}: summary exceeds {max_summary_chars} chars")
    encoded = json.dumps(item, ensure_ascii=False)
    for pattern in RAW_TEXT_RISK_PATTERNS:
        if pattern.search(encoded):
            raise ValueError(f"{kind} {ident}: tracked graph leaks private path or raw source metadata")


def validate_framework_adapters(path: Path, expected_count: int) -> None:
    text = path.read_text(encoding="utf-8")
    required_fragments = [
        "adapters:",
        "fastapi:",
        "status: verified_from_public_graph",
        "APIRouter:",
        "Depends:",
        "response_model:",
        "SQLAlchemy:",
        "spring:",
        '"@RestController":',
        '"@Service":',
        '"@Repository":',
        "JPA:",
        "OpenAPI:",
        "WebFlux:",
        "Spring Security:",
        "extension_points:",
    ]
    for fragment in required_fragments:
        if fragment not in text:
            raise ValueError(f"framework_adapters.yaml: missing {fragment}")
    actual = len(re.findall(r"status:\s+verified_from_public_graph", text))
    if actual != expected_count:
        raise ValueError(f"framework_adapters.yaml: expected {expected_count} verified adapter, got {actual}")
    for pattern in RAW_TEXT_RISK_PATTERNS:
        if pattern.search(text):
            raise ValueError("framework_adapters.yaml: leaks private path or raw source metadata")


def validate_graph(references_dir: Path) -> None:
    manifest_path = references_dir / "graph_manifest.json"
    nodes_path = references_dir / "nodes.jsonl"
    edges_path = references_dir / "edges.jsonl"
    chunks_path = references_dir / "chunks.jsonl"
    ontology_path = references_dir / "ontology.yaml"
    adapters_path = references_dir / "framework_adapters.yaml"
    for path in [manifest_path, nodes_path, edges_path, chunks_path, ontology_path, adapters_path]:
        if not path.is_file():
            raise ValueError(f"missing required file: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("public_sanitized") is not True:
        raise ValueError("graph_manifest.json: public_sanitized must be true")
    quality = manifest.get("source_quality_gate", {})
    if quality.get("uses_raw_ocr_source") is not False:
        raise ValueError("graph_manifest.json: must not use raw OCR source")
    if quality.get("uses_public_skill_graphs_only") is not True:
        raise ValueError("graph_manifest.json: must use public skill graphs only")

    nodes = load_jsonl(nodes_path)
    edges = load_jsonl(edges_path)
    chunks = load_jsonl(chunks_path)
    max_summary_chars = 600

    node_ids: set[str] = set()
    for node in nodes:
        require_fields("node", node, REQUIRED_NODE_FIELDS)
        ident = node["id"]
        if ident in node_ids:
            raise ValueError(f"duplicate node id: {ident}")
        node_ids.add(ident)
        if node["type"] not in NODE_TYPES:
            raise ValueError(f"node {ident}: unknown type {node['type']}")
        if not isinstance(node["aliases"], list):
            raise ValueError(f"node {ident}: aliases must be a list")
        validate_source_refs("node", ident, node["source_refs"])
        validate_public_text("node", ident, node, max_summary_chars)

    connected: set[str] = set()
    for edge in edges:
        require_fields("edge", edge, REQUIRED_EDGE_FIELDS)
        ident = f"{edge['source']}->{edge['target']}"
        if edge["source"] not in node_ids:
            raise ValueError(f"edge {ident}: unknown source")
        if edge["target"] not in node_ids:
            raise ValueError(f"edge {ident}: unknown target")
        if edge["type"] not in EDGE_TYPES:
            raise ValueError(f"edge {ident}: unknown type {edge['type']}")
        validate_source_refs("edge", ident, edge["source_refs"])
        validate_public_text("edge", ident, edge, max_summary_chars)
        connected.update([edge["source"], edge["target"]])

    orphans = sorted(node_ids - connected)
    if orphans:
        raise ValueError(f"orphan graph nodes: {orphans}")

    for chunk in chunks:
        require_fields("chunk", chunk, REQUIRED_CHUNK_FIELDS)
        ident = chunk["id"]
        if not isinstance(chunk["keywords"], list) or not chunk["keywords"]:
            raise ValueError(f"chunk {ident}: keywords must be a non-empty list")
        validate_source_refs("chunk", ident, chunk["source_refs"])
        validate_public_text("chunk", ident, chunk, max_summary_chars)

    counts = manifest.get("counts", {})
    expected = {"nodes": len(nodes), "edges": len(edges), "chunks": len(chunks)}
    if counts.get("nodes") != expected["nodes"] or counts.get("edges") != expected["edges"] or counts.get("chunks") != expected["chunks"]:
        raise ValueError(f"graph_manifest.json counts mismatch: expected {expected}, got {counts}")
    adapter_count = int(manifest.get("framework_adapters_count", 0))
    validate_framework_adapters(adapters_path, adapter_count)

    print(f"Graph valid: {len(nodes)} nodes, {len(edges)} edges, {len(chunks)} chunks, {adapter_count} adapter")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references_dir", nargs="?", default=Path(__file__).resolve().parents[1] / "references")
    args = parser.parse_args()
    try:
        validate_graph(Path(args.references_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
